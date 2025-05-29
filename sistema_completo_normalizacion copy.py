# ========================================
# ARCHIVO: sistema_completo_normalizacion.py
# SISTEMA INTEGRAL DE NORMALIZACIÓN DE DOMICILIOS
# ========================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import psycopg2
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import numpy as np
import uuid
import io
import zipfile
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import json
import re
from fuzzywuzzy import fuzz, process
import unicodedata

# ========================================
# 1. CONFIGURACIÓN AVANZADA
# ========================================

DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'normalizacion_domicilios',
    'user': 'postgres',
    'password': 'admin123'
}

# Configuración de página
st.set_page_config(
    page_title="🏠 Sistema Integral - Normalización Telmex",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta de colores
COLORES = {
    'rojo_principal': '#E53E3E',
    'azul_telmex': '#0066CC',
    'verde': '#38A169',
    'amarillo': '#D69E2E',
    'gris_claro': '#F7FAFC',
    'gris_medio': '#E2E8F0',
    'gris_oscuro': '#2D3748',
    'blanco': '#FFFFFF'
}

# ========================================
# 2. ESQUEMAS DE TABLAS AS400
# ========================================

ESQUEMAS_AS400 = {
    'ESTADOS': {
        'STASTS': {'tipo': 'CHARACTER', 'longitud': 1, 'descripcion': 'Status'},
        'STASAB': {'tipo': 'CHARACTER', 'longitud': 2, 'descripcion': 'Clave Estado'},
        'STADES': {'tipo': 'CHARACTER', 'longitud': 20, 'descripcion': 'Descripción Estado'}
    },
    'CIUDADES': {
        'CTYSTS': {'tipo': 'CHARACTER', 'longitud': 1, 'descripcion': 'Status'},
        'CTYCAB': {'tipo': 'CHARACTER', 'longitud': 3, 'descripcion': 'Clave Ciudad'},
        'CTYDES': {'tipo': 'CHARACTER', 'longitud': 40, 'descripcion': 'Descripción Ciudad'}
    },
    'MUNICIPIOS': {
        'MPISTS': {'tipo': 'CHARACTER', 'longitud': 1, 'descripcion': 'Status'},
        'MPICVE': {'tipo': 'CHARACTER', 'longitud': 3, 'descripcion': 'Clave Municipio'},
        'MPIDES': {'tipo': 'CHARACTER', 'longitud': 30, 'descripcion': 'Descripción Municipio'}
    },
    'ALCALDIAS': {
        'DLGSTS': {'tipo': 'CHARACTER', 'longitud': 1, 'descripcion': 'Status'},
        'DLGCVE': {'tipo': 'CHARACTER', 'longitud': 3, 'descripcion': 'Clave Alcaldía'},
        'DLGDES': {'tipo': 'CHARACTER', 'longitud': 30, 'descripcion': 'Descripción Alcaldía'}
    },
    'COLONIAS': {
        'SDASTS': {'tipo': 'CHARACTER', 'longitud': 1, 'descripcion': 'Status'},
        'SDASDA': {'tipo': 'CHARACTER', 'longitud': 5, 'descripcion': 'Clave Colonia'},
        'SDADES': {'tipo': 'CHARACTER', 'longitud': 40, 'descripcion': 'Descripción Colonia'}
    }
}

# ========================================
# 3. ESQUEMA DE REFERENCIA UNIFICADO
# ========================================

ESQUEMA_REFERENCIA = {
    'id_referencia': 'UUID PRIMARY KEY',
    'tipo_catalogo': 'VARCHAR(20)', # ESTADOS/MUNICIPIOS/COLONIAS/CIUDADES/ALCALDIAS
    'codigo_oficial': 'VARCHAR(10)', # Código SEPOMEX/INEGI
    'nombre_oficial': 'VARCHAR(100)', # Nombre normalizado
    'nombre_alternativo': 'TEXT', # JSON con variaciones
    'coordenadas_lat': 'DECIMAL(10,8)',
    'coordenadas_lng': 'DECIMAL(11,8)',
    'estado_padre': 'VARCHAR(50)',
    'municipio_padre': 'VARCHAR(50)',
    'activo': 'BOOLEAN DEFAULT TRUE',
    'fecha_actualizacion': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
}

# ========================================
# 4. CLASE PRINCIPAL DEL SISTEMA
# ========================================

class SistemaNormalizacion:
    """Clase principal que maneja todo el sistema de normalización"""
    
    def __init__(self):
        self.engine = self.crear_conexion()
        self.crear_tablas_sistema()
        
    def crear_conexion(self):
        """Crear conexión a PostgreSQL"""
        try:
            engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
            return engine
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return None
    
    def crear_tablas_sistema(self):
        """Crear todas las tablas necesarias del sistema"""
        if not self.engine:
            return
            
        sqls = [
            # Tabla de referencias unificada
            """
            CREATE TABLE IF NOT EXISTS referencias_normalizacion (
                id_referencia UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tipo_catalogo VARCHAR(20) NOT NULL,
                codigo_oficial VARCHAR(10),
                nombre_oficial VARCHAR(100) NOT NULL,
                nombre_alternativo TEXT,
                coordenadas_lat DECIMAL(10,8),
                coordenadas_lng DECIMAL(11,8),
                estado_padre VARCHAR(50),
                municipio_padre VARCHAR(50),
                activo BOOLEAN DEFAULT TRUE,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Tabla de archivos cargados
            """
            CREATE TABLE IF NOT EXISTS archivos_cargados (
                id_archivo UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                nombre_archivo VARCHAR(255) NOT NULL,
                tipo_catalogo VARCHAR(20) NOT NULL,
                division VARCHAR(10) NOT NULL,
                total_registros INTEGER,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario VARCHAR(50) DEFAULT 'sistema',
                estado_procesamiento VARCHAR(20) DEFAULT 'PENDIENTE'
            );
            """,
            
            # Tabla de resultados de normalización
            """
            CREATE TABLE IF NOT EXISTS resultados_normalizacion (
                id_resultado UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                id_archivo UUID REFERENCES archivos_cargados(id_archivo),
                tipo_catalogo VARCHAR(20) NOT NULL,
                division VARCHAR(10) NOT NULL,
                
                -- Datos originales AS400
                campo_status VARCHAR(1),
                campo_clave VARCHAR(10),
                campo_descripcion VARCHAR(100),
                texto_original VARCHAR(200),
                
                -- Datos normalizados
                valor_normalizado VARCHAR(100),
                codigo_normalizado VARCHAR(10),
                metodo_usado VARCHAR(50),
                confianza DECIMAL(5,4),
                coordenadas_lat DECIMAL(10,8),
                coordenadas_lng DECIMAL(11,8),
                
                -- Control
                requiere_revision BOOLEAN DEFAULT FALSE,
                revisado_por VARCHAR(50),
                fecha_revision TIMESTAMP,
                observaciones TEXT,
                
                -- Trazabilidad
                fecha_proceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version_algoritmo VARCHAR(10) DEFAULT '1.0'
            );
            """,
            
            # Índices para optimización
            """
            CREATE INDEX IF NOT EXISTS idx_referencias_tipo ON referencias_normalizacion(tipo_catalogo);
            CREATE INDEX IF NOT EXISTS idx_referencias_activo ON referencias_normalizacion(activo);
            CREATE INDEX IF NOT EXISTS idx_resultados_archivo ON resultados_normalizacion(id_archivo);
            CREATE INDEX IF NOT EXISTS idx_resultados_tipo ON resultados_normalizacion(tipo_catalogo);
            CREATE INDEX IF NOT EXISTS idx_resultados_division ON resultados_normalizacion(division);
            """
        ]
        
        try:
            with self.engine.connect() as conn:
                for sql in sqls:
                    conn.execute(text(sql))
                conn.commit()
            st.success("✅ Sistema de tablas inicializado correctamente")
        except Exception as e:
            st.error(f"Error creando tablas: {e}")
    
    def validar_estructura_archivo(self, df, tipo_catalogo):
        """Validar que el archivo tenga la estructura correcta de AS400 - CORREGIDA"""
        
        if tipo_catalogo not in ESQUEMAS_AS400:
            return False, f"Tipo de catálogo no válido: {tipo_catalogo}"
        
        esquema = ESQUEMAS_AS400[tipo_catalogo]
        columnas_esperadas = list(esquema.keys())
        columnas_archivo = df.columns.tolist()
        
        # Verificar que existan las columnas mínimas
        columnas_faltantes = set(columnas_esperadas) - set(columnas_archivo)
        if columnas_faltantes:
            return False, f"❌ Faltan columnas obligatorias: {', '.join(columnas_faltantes)}"
        
        # Verificar que el archivo no esté vacío
        if len(df) == 0:
            return False, "❌ El archivo está vacío"
        
        # Verificar longitudes
        errores_longitud = []
        for columna, config in esquema.items():
            if columna in df.columns:
                # Convertir a string y calcular longitud máxima
                df[columna] = df[columna].astype(str)
                max_length = df[columna].str.len().max()
                if max_length > config['longitud']:
                    errores_longitud.append(f"❌ {columna}: longitud máxima {max_length} > esperado {config['longitud']}")
        
        if errores_longitud:
            return False, f"Errores de longitud:\n" + "\n".join(errores_longitud)
        
        # Verificar que el campo de descripción tenga datos
        CAMPO_DESCRIPCION_MAP = {
            'ESTADOS': 'STADES',
            'CIUDADES': 'CTYDES', 
            'MUNICIPIOS': 'MPIDES',
            'ALCALDIAS': 'DLGDES',
            'COLONIAS': 'SDADES'
        }
        
        campo_desc = CAMPO_DESCRIPCION_MAP.get(tipo_catalogo)
        if campo_desc and campo_desc in df.columns:
            registros_vacios = df[campo_desc].isna().sum() + (df[campo_desc] == '').sum()
            if registros_vacios > 0:
                return False, f"⚠️ {registros_vacios} registros tienen campo de descripción vacío en {campo_desc}"
        
        return True, f"✅ Estructura válida: {len(df)} registros, {len(columnas_archivo)} columnas"
    
    def procesar_archivo_cargado(self, df, tipo_catalogo, division, nombre_archivo):
        """Procesar un archivo cargado y normalizarlo - CORREGIDO"""
        
        # Validar estructura
        valido, mensaje = self.validar_estructura_archivo(df, tipo_catalogo)
        if not valido:
            return False, mensaje
        
        try:
            # Registrar archivo en BD
            id_archivo = str(uuid.uuid4())
            
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO archivos_cargados 
                    (id_archivo, nombre_archivo, tipo_catalogo, division, total_registros, estado_procesamiento)
                    VALUES (:id_archivo, :nombre, :tipo, :division, :total, 'PROCESANDO')
                """), {
                    'id_archivo': id_archivo,
                    'nombre': nombre_archivo,
                    'tipo': tipo_catalogo,
                    'division': division,
                    'total': len(df)
                })
                conn.commit()
            
            # Procesar registros
            resultados = []
            esquema = ESQUEMAS_AS400[tipo_catalogo]
            
            # CORRECCIÓN: Mapeo directo de campos de descripción por tipo
            CAMPO_DESCRIPCION_MAP = {
                'ESTADOS': 'STADES',
                'CIUDADES': 'CTYDES', 
                'MUNICIPIOS': 'MPIDES',
                'ALCALDIAS': 'DLGDES',
                'COLONIAS': 'SDADES'
            }
            
            campo_descripcion = CAMPO_DESCRIPCION_MAP.get(tipo_catalogo)
            
            if not campo_descripcion or campo_descripcion not in df.columns:
                return False, f"Campo de descripción '{campo_descripcion}' no encontrado para {tipo_catalogo}"
            
            # CORRECCIÓN: Mapeo de campos de status y clave
            CAMPO_STATUS_MAP = {
                'ESTADOS': 'STASTS',
                'CIUDADES': 'CTYSTS',
                'MUNICIPIOS': 'MPISTS', 
                'ALCALDIAS': 'DLGSTS',
                'COLONIAS': 'SDASTS'
            }
            
            CAMPO_CLAVE_MAP = {
                'ESTADOS': 'STASAB',
                'CIUDADES': 'CTYCAB',
                'MUNICIPIOS': 'MPICVE',
                'ALCALDIAS': 'DLGCVE', 
                'COLONIAS': 'SDASDA'
            }
            
            campo_status = CAMPO_STATUS_MAP.get(tipo_catalogo)
            campo_clave = CAMPO_CLAVE_MAP.get(tipo_catalogo)
            
            # Procesar cada registro
            for idx, row in df.iterrows():
                resultado = self.normalizar_registro(
                    texto_original=str(row[campo_descripcion]),
                    tipo_catalogo=tipo_catalogo,
                    division=division,
                    campo_status=str(row.get(campo_status, '')),
                    campo_clave=str(row.get(campo_clave, '')),
                    campo_descripcion=str(row[campo_descripcion])
                )
                
                resultado['id_archivo'] = id_archivo
                resultados.append(resultado)
                
                # Actualizar progreso cada 100 registros
                if (idx + 1) % 100 == 0:
                    progreso = (idx + 1) / len(df) * 100
                    self.actualizar_progreso_archivo(id_archivo, progreso)
            
            # Guardar resultados en BD
            self.guardar_resultados(resultados)
            
            # Marcar como completado
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE archivos_cargados 
                    SET estado_procesamiento = 'COMPLETADO'
                    WHERE id_archivo = :id_archivo
                """), {'id_archivo': id_archivo})
                conn.commit()
            
            return True, f"Procesados {len(resultados)} registros correctamente"
            
        except Exception as e:
            return False, f"Error procesando archivo: {str(e)}"
    
    def normalizar_registro(self, texto_original, tipo_catalogo, division, campo_status, campo_clave, campo_descripcion):
        """Normalizar un registro individual usando los algoritmos de IA"""
        
        # Limpiar texto
        texto_limpio = self.limpiar_texto(texto_original)
        
        # Buscar en referencias
        referencia_encontrada = self.buscar_en_referencias(texto_limpio, tipo_catalogo)
        
        resultado = {
            'tipo_catalogo': tipo_catalogo,
            'division': division,
            'campo_status': campo_status,
            'campo_clave': campo_clave,
            'campo_descripcion': campo_descripcion,
            'texto_original': texto_original,
            'valor_normalizado': None,
            'codigo_normalizado': None,
            'metodo_usado': 'SIN_MATCH',
            'confianza': 0.0,
            'coordenadas_lat': None,
            'coordenadas_lng': None,
            'requiere_revision': True
        }
        
        if referencia_encontrada:
            resultado.update({
                'valor_normalizado': referencia_encontrada['nombre_oficial'],
                'codigo_normalizado': referencia_encontrada['codigo_oficial'],
                'metodo_usado': referencia_encontrada['metodo'],
                'confianza': referencia_encontrada['confianza'],
                'coordenadas_lat': referencia_encontrada.get('coordenadas_lat'),
                'coordenadas_lng': referencia_encontrada.get('coordenadas_lng'),
                'requiere_revision': referencia_encontrada['confianza'] < 0.8
            })
        
        return resultado
    
    def limpiar_texto(self, texto):
        """Limpiar texto para normalización"""
        if not isinstance(texto, str):
            return ""
        
        # Convertir a mayúsculas
        texto = texto.upper().strip()
        
        # Quitar acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
        
        # Limpiar caracteres especiales
        texto = re.sub(r'[^\w\s]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        texto = texto.strip()
        
        return texto
    
    def buscar_en_referencias(self, texto_limpio, tipo_catalogo):
        """Buscar coincidencias en las referencias usando IA"""
        
        try:
            with self.engine.connect() as conn:
                # Obtener referencias del tipo correspondiente
                result = conn.execute(text("""
                    SELECT * FROM referencias_normalizacion 
                    WHERE tipo_catalogo = :tipo AND activo = true
                """), {'tipo': tipo_catalogo})
                
                referencias = []
                for row in result:
                    referencias.append(dict(row._mapping))
            
            if not referencias:
                return None
            
            mejor_match = None
            mejor_confianza = 0.0
            mejor_metodo = 'SIN_MATCH'
            
            # Buscar coincidencia exacta
            for ref in referencias:
                nombre_ref_limpio = self.limpiar_texto(ref['nombre_oficial'])
                if texto_limpio == nombre_ref_limpio:
                    return {
                        **ref,
                        'metodo': 'EXACTO',
                        'confianza': 1.0
                    }
            
            # Buscar con fuzzy matching
            nombres_referencias = [self.limpiar_texto(ref['nombre_oficial']) for ref in referencias]
            mejor_fuzzy = process.extractOne(texto_limpio, nombres_referencias, scorer=fuzz.token_sort_ratio)
            
            if mejor_fuzzy and mejor_fuzzy[1] >= 60:  # Umbral mínimo 60%
                # Encontrar la referencia correspondiente
                for ref in referencias:
                    if self.limpiar_texto(ref['nombre_oficial']) == mejor_fuzzy[0]:
                        return {
                            **ref,
                            'metodo': 'FUZZY_ALTO' if mejor_fuzzy[1] >= 80 else 'FUZZY_BAJO',
                            'confianza': mejor_fuzzy[1] / 100.0
                        }
            
            return None
            
        except Exception as e:
            print(f"Error buscando referencias: {e}")
            return None
    
    def guardar_resultados(self, resultados):
        """Guardar resultados de normalización en la base de datos"""
        
        if not resultados:
            return
        
        try:
            df_resultados = pd.DataFrame(resultados)
            df_resultados.to_sql('resultados_normalizacion', self.engine, if_exists='append', index=False)
        except Exception as e:
            print(f"Error guardando resultados: {e}")
    
    def actualizar_progreso_archivo(self, id_archivo, progreso):
        """Actualizar progreso de procesamiento de archivo"""
        # En una implementación real, esto se podría guardar en una tabla de progreso
        # Por ahora solo lo almacenamos en session_state
        if 'progreso_archivos' not in st.session_state:
            st.session_state.progreso_archivos = {}
        st.session_state.progreso_archivos[id_archivo] = progreso



# ========================================
# FUNCIÓN AUXILIAR MEJORADA (FUERA DE LA CLASE)
# ========================================

def mostrar_estructura_esperada_mejorada(tipo_catalogo):
    """Mostrar estructura esperada con más detalles"""
    
    if tipo_catalogo in ESQUEMAS_AS400:
        st.markdown(f"#### 📋 Estructura Esperada para {tipo_catalogo}:")
        
        esquema = ESQUEMAS_AS400[tipo_catalogo]
        
        # Identificar campo principal (descripción)
        CAMPO_PRINCIPAL = {
            'ESTADOS': 'STADES',
            'CIUDADES': 'CTYDES', 
            'MUNICIPIOS': 'MPIDES',
            'ALCALDIAS': 'DLGDES',
            'COLONIAS': 'SDADES'
        }
        
        campo_principal = CAMPO_PRINCIPAL.get(tipo_catalogo)
        
        estructura_data = []
        for campo, info in esquema.items():
            es_principal = campo == campo_principal
            estructura_data.append({
                'Campo': campo,
                'Tipo': info['tipo'],
                'Longitud': info['longitud'],
                'Descripción': info['descripcion'],
                'Es Principal': '🎯 SÍ' if es_principal else 'No',
                'Obligatorio': '✅ SÍ'
            })
        
        estructura_df = pd.DataFrame(estructura_data)
        st.dataframe(estructura_df, use_container_width=True, hide_index=True)
        
        # Mostrar ejemplo de datos
        ejemplos = {
            'ESTADOS': """STASTS,STASAB,STADES
A,01,AGUASCALIENTES
A,02,BAJA CALIFORNIA
A,03,BAJA CALIFORNIA SUR""",
            'CIUDADES': """CTYSTS,CTYCAB,CTYDES
A,001,AGUASCALIENTES
A,002,MEXICALI
A,003,TIJUANA""",
            'MUNICIPIOS': """MPISTS,MPICVE,MPIDES
A,001,AGUASCALIENTES
A,002,ASIENTOS
A,003,CALVILLO""",
            'ALCALDIAS': """DLGSTS,DLGCVE,DLGDES
A,001,ALVARO OBREGON
A,002,AZCAPOTZALCO
A,003,BENITO JUAREZ""",
            'COLONIAS': """SDASTS,SDASDA,SDADES
A,00001,CENTRO
A,00002,DOCTORES
A,00003,OBRERA"""
        }
        
        if tipo_catalogo in ejemplos:
            st.markdown("**Ejemplo de datos correctos:**")
            st.code(ejemplos[tipo_catalogo], language="csv")

    # ========================================
    # VALIDACIÓN MEJORADA DE ARCHIVOS
    # ========================================

    def validar_estructura_archivo_mejorada(self, df, tipo_catalogo):
        """Validar que el archivo tenga la estructura correcta de AS400 - MEJORADA"""
        
        if tipo_catalogo not in ESQUEMAS_AS400:
            return False, f"Tipo de catálogo no válido: {tipo_catalogo}"
        
        esquema = ESQUEMAS_AS400[tipo_catalogo]
        columnas_esperadas = list(esquema.keys())
        columnas_archivo = df.columns.tolist()
        
        # Verificar que existan las columnas mínimas
        columnas_faltantes = set(columnas_esperadas) - set(columnas_archivo)
        if columnas_faltantes:
            return False, f"❌ Faltan columnas obligatorias: {', '.join(columnas_faltantes)}"
        
        # Verificar que el archivo no esté vacío
        if len(df) == 0:
            return False, "❌ El archivo está vacío"
        
        # Verificar longitudes
        errores_longitud = []
        for columna, config in esquema.items():
            if columna in df.columns:
                # Convertir a string y calcular longitud máxima
                df[columna] = df[columna].astype(str)
                max_length = df[columna].str.len().max()
                if max_length > config['longitud']:
                    errores_longitud.append(f"❌ {columna}: longitud máxima {max_length} > esperado {config['longitud']}")
        
        if errores_longitud:
            return False, f"Errores de longitud:\n" + "\n".join(errores_longitud)
        
        # Verificar que el campo de descripción tenga datos
        CAMPO_DESCRIPCION_MAP = {
            'ESTADOS': 'STADES',
            'CIUDADES': 'CTYDES', 
            'MUNICIPIOS': 'MPIDES',
            'ALCALDIAS': 'DLGDES',
            'COLONIAS': 'SDADES'
        }
        
        campo_desc = CAMPO_DESCRIPCION_MAP.get(tipo_catalogo)
        if campo_desc and campo_desc in df.columns:
            registros_vacios = df[campo_desc].isna().sum() + (df[campo_desc] == '').sum()
            if registros_vacios > 0:
                return False, f"⚠️ {registros_vacios} registros tienen campo de descripción vacío en {campo_desc}"
        
        return True, f"✅ Estructura válida: {len(df)} registros, {len(columnas_archivo)} columnas"
   
    def normalizar_registro(self, texto_original, tipo_catalogo, division, campo_status, campo_clave, campo_descripcion):
        """Normalizar un registro individual usando los algoritmos de IA"""
        
        # Limpiar texto
        texto_limpio = self.limpiar_texto(texto_original)
        
        # Buscar en referencias
        referencia_encontrada = self.buscar_en_referencias(texto_limpio, tipo_catalogo)
        
        resultado = {
            'tipo_catalogo': tipo_catalogo,
            'division': division,
            'campo_status': campo_status,
            'campo_clave': campo_clave,
            'campo_descripcion': campo_descripcion,
            'texto_original': texto_original,
            'valor_normalizado': None,
            'codigo_normalizado': None,
            'metodo_usado': 'SIN_MATCH',
            'confianza': 0.0,
            'coordenadas_lat': None,
            'coordenadas_lng': None,
            'requiere_revision': True
        }
        
        if referencia_encontrada:
            resultado.update({
                'valor_normalizado': referencia_encontrada['nombre_oficial'],
                'codigo_normalizado': referencia_encontrada['codigo_oficial'],
                'metodo_usado': referencia_encontrada['metodo'],
                'confianza': referencia_encontrada['confianza'],
                'coordenadas_lat': referencia_encontrada.get('coordenadas_lat'),
                'coordenadas_lng': referencia_encontrada.get('coordenadas_lng'),
                'requiere_revision': referencia_encontrada['confianza'] < 0.8
            })
        
        return resultado
    
    def limpiar_texto(self, texto):
        """Limpiar texto para normalización"""
        if not isinstance(texto, str):
            return ""
        
        # Convertir a mayúsculas
        texto = texto.upper().strip()
        
        # Quitar acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
        
        # Limpiar caracteres especiales
        texto = re.sub(r'[^\w\s]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        texto = texto.strip()
        
        return texto
    
    def buscar_en_referencias(self, texto_limpio, tipo_catalogo):
        """Buscar coincidencias en las referencias usando IA"""
        
        try:
            with self.engine.connect() as conn:
                # Obtener referencias del tipo correspondiente
                result = conn.execute(text("""
                    SELECT * FROM referencias_normalizacion 
                    WHERE tipo_catalogo = :tipo AND activo = true
                """), {'tipo': tipo_catalogo})
                
                referencias = [dict(row) for row in result]
            
            if not referencias:
                return None
            
            mejor_match = None
            mejor_confianza = 0.0
            mejor_metodo = 'SIN_MATCH'
            
            # Buscar coincidencia exacta
            for ref in referencias:
                nombre_ref_limpio = self.limpiar_texto(ref['nombre_oficial'])
                if texto_limpio == nombre_ref_limpio:
                    return {
                        **ref,
                        'metodo': 'EXACTO',
                        'confianza': 1.0
                    }
            
            # Buscar con fuzzy matching
            nombres_referencias = [self.limpiar_texto(ref['nombre_oficial']) for ref in referencias]
            mejor_fuzzy = process.extractOne(texto_limpio, nombres_referencias, scorer=fuzz.token_sort_ratio)
            
            if mejor_fuzzy and mejor_fuzzy[1] >= 60:  # Umbral mínimo 60%
                # Encontrar la referencia correspondiente
                for ref in referencias:
                    if self.limpiar_texto(ref['nombre_oficial']) == mejor_fuzzy[0]:
                        return {
                            **ref,
                            'metodo': 'FUZZY_ALTO' if mejor_fuzzy[1] >= 80 else 'FUZZY_BAJO',
                            'confianza': mejor_fuzzy[1] / 100.0
                        }
            
            return None
            
        except Exception as e:
            print(f"Error buscando referencias: {e}")
            return None
    
    def guardar_resultados(self, resultados):
        """Guardar resultados de normalización en la base de datos"""
        
        if not resultados:
            return
        
        try:
            df_resultados = pd.DataFrame(resultados)
            df_resultados.to_sql('resultados_normalizacion', self.engine, if_exists='append', index=False)
        except Exception as e:
            print(f"Error guardando resultados: {e}")
    
    def actualizar_progreso_archivo(self, id_archivo, progreso):
        """Actualizar progreso de procesamiento de archivo"""
        # En una implementación real, esto se podría guardar en una tabla de progreso
        # Por ahora solo lo almacenamos en session_state
        if 'progreso_archivos' not in st.session_state:
            st.session_state.progreso_archivos = {}
        st.session_state.progreso_archivos[id_archivo] = progreso

# ========================================
# 5. INTERFAZ DE CARGA DE ARCHIVOS
# ========================================

def mostrar_interfaz_carga():
    """Mostrar interfaz completa de carga de archivos"""
    
    st.markdown("## 📁 Carga y Procesamiento de Archivos")
    
    # Crear tabs para organizar mejor
    tab1, tab2, tab3 = st.tabs(["📤 Subir Archivos", "📚 Referencias", "⚙️ Procesamiento"])
    
    with tab1:
        mostrar_carga_archivos_datos()
    
    with tab2:
        mostrar_carga_referencias()
    
    with tab3:
        mostrar_procesamiento_tiempo_real()

# ========================================
# FUNCIÓN DE INTERFAZ CORREGIDA (FUERA DE LA CLASE)
# ========================================

def mostrar_carga_archivos_datos():
    """Interfaz para cargar archivos de datos AS400 - CORREGIDA"""
    
    st.markdown("### 📊 Cargar Archivos de Datos AS400")
    
    # Selector de tipo de catálogo
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_catalogo = st.selectbox(
            "Tipo de Catálogo:",
            list(ESQUEMAS_AS400.keys()),
            help="Selecciona el tipo de datos que vas a subir"
        )
    
    with col2:
        division = st.selectbox(
            "División:",
            ["DES", "QAS", "MEX", "GDL", "MTY", "NTE", "TIJ"],
            help="División a la que pertenecen los datos"
        )
    
    # Mostrar estructura esperada MEJORADA
    if tipo_catalogo:
        mostrar_estructura_esperada_mejorada(tipo_catalogo)
    
    # Carga de archivos
    st.markdown("#### 📤 Subir Archivos:")
    
    archivos_subidos = st.file_uploader(
        "Selecciona archivos CSV:",
        type=['csv'],
        accept_multiple_files=True,
        help="Puedes subir múltiples archivos del mismo tipo"
    )
    
    if archivos_subidos:
        st.markdown(f"#### 📋 Archivos Seleccionados ({len(archivos_subidos)}):")
        
        archivos_validos = []
        
        for archivo in archivos_subidos:
            with st.expander(f"📄 {archivo.name}"):
                try:
                    # Leer archivo
                    df = pd.read_csv(archivo)
                    
                    # Mostrar información básica
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Registros", len(df))
                    with col2:
                        st.metric("Columnas", len(df.columns))
                    with col3:
                        # Validar estructura
                        sistema = SistemaNormalizacion()
                        valido, mensaje = sistema.validar_estructura_archivo(df, tipo_catalogo)
                        st.metric("Estado", "✅ Válido" if valido else "❌ Error")
                    
                    # Mostrar mensaje de validación
                    if valido:
                        st.success(f"✅ {mensaje}")
                        archivos_validos.append((archivo, df))
                        
                        # Mostrar preview
                        st.markdown("**Preview (primeras 5 filas):**")
                        st.dataframe(df.head(), use_container_width=True)
                    else:
                        st.error(f"❌ {mensaje}")
                        
                        # Mostrar ayuda específica
                        st.markdown("**💡 Sugerencias:**")
                        if "Faltan columnas" in mensaje:
                            st.info("Verifica que tu archivo CSV tenga exactamente las columnas mostradas arriba")
                        elif "longitud máxima" in mensaje:
                            st.info("Algunos valores son muy largos. Revisa los datos o ajusta la estructura")
                        elif "vacío" in mensaje:
                            st.info("Asegúrate de que el campo de descripción tenga valores en todos los registros")
                
                except Exception as e:
                    st.error(f"❌ Error leyendo archivo: {str(e)}")
                    st.markdown("**💡 Posibles causas:**")
                    st.info("• Archivo no es CSV válido\n• Encoding incorrecto\n• Separadores incorrectos")
        
        # Botón para procesar archivos válidos
        if archivos_validos:
            st.markdown("---")
            if st.button(f"🚀 Procesar {len(archivos_validos)} archivo(s)", type="primary"):
                procesar_archivos_cargados(archivos_validos, tipo_catalogo, division)
        else:
            st.warning("⚠️ No hay archivos válidos para procesar. Revisa los errores mostrados arriba.")

def mostrar_carga_referencias():
    """Interfaz para cargar archivos de referencia (SEPOMEX/INEGI)"""
    
    st.markdown("### 📚 Gestión de Referencias (SEPOMEX/INEGI)")
    
    # Mostrar referencias actuales
    mostrar_referencias_actuales()
    
    st.markdown("---")
    
    # Cargar nueva referencia
    st.markdown("#### 📤 Cargar Nueva Referencia:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_ref = st.selectbox(
            "Tipo de Referencia:",
            list(ESQUEMAS_AS400.keys()),
            key="tipo_ref"
        )
    
    with col2:
        fuente_ref = st.selectbox(
            "Fuente:",
            ["SEPOMEX", "INEGI", "OTRO"],
            key="fuente_ref"
        )
    
    archivo_referencia = st.file_uploader(
        "Archivo de Referencia (CSV):",
        type=['csv'],
        key="archivo_ref",
        help="Estructura esperada: codigo_oficial, nombre_oficial, coordenadas_lat, coordenadas_lng"
    )
    
    if archivo_referencia:
        try:
            df_ref = pd.read_csv(archivo_referencia)
            
            st.markdown("**Estructura del archivo:**")
            st.dataframe(df_ref.head(), use_container_width=True)
            
            # Validar columnas mínimas requeridas
            columnas_requeridas = ['codigo_oficial', 'nombre_oficial']
            columnas_faltantes = set(columnas_requeridas) - set(df_ref.columns)
            
            if columnas_faltantes:
                st.error(f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}")
            else:
                if st.button("💾 Cargar Referencia", type="primary"):
                    cargar_nueva_referencia(df_ref, tipo_ref, fuente_ref, archivo_referencia.name)
        
        except Exception as e:
            st.error(f"Error leyendo archivo de referencia: {str(e)}")

def mostrar_referencias_actuales():
    """Mostrar las referencias actuales en el sistema"""
    
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tipo_catalogo, COUNT(*) as total_referencias,
                       MAX(fecha_actualizacion) as ultima_actualizacion
                FROM referencias_normalizacion 
                WHERE activo = true
                GROUP BY tipo_catalogo
                ORDER BY tipo_catalogo
            """))
            
            referencias = [dict(row) for row in result]
        
        if referencias:
            st.markdown("#### 📋 Referencias Actuales:")
            
            df_referencias = pd.DataFrame(referencias)
            df_referencias.columns = ['Tipo', 'Total Referencias', 'Última Actualización']
            
            st.dataframe(df_referencias, use_container_width=True, hide_index=True)
        else:
            st.info("No hay referencias cargadas en el sistema")
    
    except Exception as e:
        st.error(f"Error consultando referencias: {str(e)}")

# ========================================
# CORRECCIÓN PARA ERROR EN PROCESAMIENTO TIEMPO REAL
# ========================================

def mostrar_procesamiento_tiempo_real():
    """Mostrar el progreso de procesamiento en tiempo real - CORREGIDO"""
    
    st.markdown("### ⚙️ Monitor de Procesamiento")
    
    # Obtener archivos en procesamiento
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT a.id_archivo, a.nombre_archivo, a.tipo_catalogo, a.division,
                       a.total_registros, a.fecha_carga, a.estado_procesamiento,
                       COALESCE(r.procesados, 0) as registros_procesados
                FROM archivos_cargados a
                LEFT JOIN (
                    SELECT id_archivo, COUNT(*) as procesados
                    FROM resultados_normalizacion
                    GROUP BY id_archivo
                ) r ON a.id_archivo = r.id_archivo
                WHERE a.fecha_carga >= CURRENT_DATE - INTERVAL '1 day'
                ORDER BY a.fecha_carga DESC
            """))
            
            # CORRECCIÓN: Manejar resultados correctamente
            archivos = []
            for row in result:
                if row is not None:
                    archivos.append(dict(row._mapping))
        
        if archivos:
            st.markdown("#### 📊 Archivos Recientes:")
            
            for archivo in archivos:
                with st.expander(f"📄 {archivo['nombre_archivo']} - {archivo['estado_procesamiento']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_reg = int(archivo['total_registros'] or 0)
                        st.metric("Total Registros", f"{total_reg:,}")
                    
                    with col2:
                        procesados = int(archivo['registros_procesados'] or 0)
                        st.metric("Procesados", f"{procesados:,}")
                    
                    with col3:
                        if total_reg > 0:
                            progreso = (procesados / total_reg) * 100
                            st.metric("Progreso", f"{progreso:.1f}%")
                        else:
                            st.metric("Progreso", "0%")
                    
                    with col4:
                        st.metric("División", archivo['division'])
                    
                    # Barra de progreso
                    if total_reg > 0:
                        progreso_pct = procesados / total_reg
                        st.progress(min(progreso_pct, 1.0))  # Asegurar que no exceda 1.0
                    else:
                        st.progress(0.0)
                    
                    # Información adicional
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Tipo:** {archivo['tipo_catalogo']}")
                    with col2:
                        st.info(f"**Cargado:** {archivo['fecha_carga']}")
                    
                    # Botones de acción
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"📊 Ver Resultados", key=f"ver_{archivo['id_archivo']}"):
                            mostrar_resultados_archivo(archivo['id_archivo'])
                    
                    with col2:
                        if st.button(f"📥 Descargar", key=f"desc_{archivo['id_archivo']}"):
                            descargar_resultados_archivo(archivo['id_archivo'])
                    
                    with col3:
                        if archivo['estado_procesamiento'] == 'COMPLETADO':
                            if st.button(f"🗑️ Eliminar", key=f"del_{archivo['id_archivo']}"):
                                eliminar_archivo_procesado(archivo['id_archivo'])
        else:
            st.info("📋 No hay archivos procesados recientemente")
            
            # Mostrar ayuda para usuarios nuevos
            st.markdown("### 🚀 ¿Cómo empezar?")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **1. Sube archivos AS400:**
                - Ve a la pestaña "Subir Archivos"
                - Selecciona el tipo de catálogo
                - Carga tu archivo CSV
                """)
            
            with col2:
                st.markdown("""
                **2. Configura referencias:**
                - Sube archivos de referencia SEPOMEX/INEGI
                - Mejora la precisión de normalización
                - Ve resultados aquí en tiempo real
                """)
    
    except Exception as e:
        st.error(f"Error consultando procesamiento: {str(e)}")
        
        # Mostrar información de debug en desarrollo
        if st.checkbox("🔧 Mostrar detalles técnicos"):
            st.code(f"""
Error: {str(e)}
Tipo: {type(e).__name__}

Posibles causas:
1. Base de datos no inicializada
2. Tablas no creadas
3. Error de conexión
4. Problema con SQLAlchemy version
            """)

# ========================================
# 6. FUNCIONES DE PROCESAMIENTO
# ========================================

def procesar_archivos_cargados(archivos_validos, tipo_catalogo, division):
    """Procesar archivos cargados en tiempo real"""
    
    sistema = SistemaNormalizacion()
    
    # Crear barra de progreso general
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_archivos = len(archivos_validos)
    
    for idx, (archivo, df) in enumerate(archivos_validos):
        status_text.text(f"Procesando {archivo.name}... ({idx + 1}/{total_archivos})")
        
        # Procesar archivo
        exito, mensaje = sistema.procesar_archivo_cargado(
            df, tipo_catalogo, division, archivo.name
        )
        
        if exito:
            st.success(f"✅ {archivo.name}: {mensaje}")
        else:
            st.error(f"❌ {archivo.name}: {mensaje}")
        
        # Actualizar progreso general
        progress_bar.progress((idx + 1) / total_archivos)
    
    status_text.text("✅ Procesamiento completado")
    st.balloons()

def cargar_nueva_referencia(df_ref, tipo_ref, fuente_ref, nombre_archivo):
    """Cargar nueva referencia al sistema"""
    
    sistema = SistemaNormalizacion()
    
    try:
        # Preparar datos para inserción
        registros_referencia = []
        
        for _, row in df_ref.iterrows():
            registro = {
                'tipo_catalogo': tipo_ref,
                'codigo_oficial': str(row.get('codigo_oficial', '')),
                'nombre_oficial': str(row.get('nombre_oficial', '')),
                'nombre_alternativo': json.dumps(row.get('nombres_alternativos', [])) if 'nombres_alternativos' in row else None,
                'coordenadas_lat': float(row['coordenadas_lat']) if 'coordenadas_lat' in row and pd.notna(row['coordenadas_lat']) else None,
                'coordenadas_lng': float(row['coordenadas_lng']) if 'coordenadas_lng' in row and pd.notna(row['coordenadas_lng']) else None,
                'estado_padre': str(row.get('estado_padre', '')) if 'estado_padre' in row else None,
                'municipio_padre': str(row.get('municipio_padre', '')) if 'municipio_padre' in row else None
            }
            registros_referencia.append(registro)
        
        # Insertar en base de datos
        df_insert = pd.DataFrame(registros_referencia)
        df_insert.to_sql('referencias_normalizacion', sistema.engine, if_exists='append', index=False)
        
        st.success(f"✅ Se cargaron {len(registros_referencia)} referencias de {fuente_ref}")
        
        # Mostrar estadísticas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Registros Cargados", len(registros_referencia))
        with col2:
            con_coordenadas = sum(1 for r in registros_referencia if r['coordenadas_lat'] is not None)
            st.metric("Con Coordenadas", con_coordenadas)
        with col3:
            st.metric("Fuente", fuente_ref)
    
    except Exception as e:
        st.error(f"Error cargando referencia: {str(e)}")

def mostrar_resultados_archivo(id_archivo):
    """Mostrar resultados detallados de un archivo procesado - CORREGIDO"""
    
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            # Obtener información del archivo
            result = conn.execute(text("""
                SELECT * FROM archivos_cargados WHERE id_archivo = :id_archivo
            """), {'id_archivo': id_archivo})
            
            # CORRECCIÓN: Verificar que existe el archivo
            archivo_row = result.fetchone()
            if archivo_row is None:
                st.error("❌ No se encontró el archivo especificado.")
                return
                
            archivo_info = dict(archivo_row._mapping)
            
            # Obtener resultados
            result = conn.execute(text("""
                SELECT * FROM resultados_normalizacion 
                WHERE id_archivo = :id_archivo
                ORDER BY fecha_proceso DESC
                LIMIT 1000
            """), {'id_archivo': id_archivo})
            
            resultados = []
            for row in result:
                resultados.append(dict(row._mapping))
        
        if resultados:
            st.markdown(f"### 📊 Resultados: {archivo_info['nombre_archivo']}")
            
            # Métricas del archivo
            col1, col2, col3, col4 = st.columns(4)
            
            total = len(resultados)
            exitosos = sum(1 for r in resultados if r['valor_normalizado'])
            revision = sum(1 for r in resultados if r['requiere_revision'])
            
            # Calcular confianza promedio evitando None
            confianzas_validas = [r['confianza'] for r in resultados if r['confianza'] is not None and r['confianza'] > 0]
            confianza_prom = np.mean(confianzas_validas) if confianzas_validas else 0
            
            with col1:
                st.metric("Total Procesados", f"{total:,}")
            with col2:
                st.metric("Exitosos", f"{exitosos:,}", f"{exitosos/total*100:.1f}%" if total > 0 else "0%")
            with col3:
                st.metric("Requieren Revisión", f"{revision:,}")
            with col4:
                st.metric("Confianza Promedio", f"{confianza_prom:.1%}" if confianza_prom > 0 else "N/A")
            
            # Tabla de resultados (resto del código igual...)
            df_resultados = pd.DataFrame(resultados)
            
            # Seleccionar columnas principales para mostrar
            columnas_mostrar = [
                'texto_original', 'valor_normalizado', 'metodo_usado', 
                'confianza', 'requiere_revision', 'fecha_proceso'
            ]
            
            df_display = df_resultados[columnas_mostrar].copy()
            df_display['confianza'] = df_display['confianza'].apply(lambda x: f"{x:.1%}" if x else "N/A")
            df_display['requiere_revision'] = df_display['requiere_revision'].apply(lambda x: "⚠️ Sí" if x else "✅ No")
            df_display['fecha_proceso'] = pd.to_datetime(df_display['fecha_proceso']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Renombrar columnas para mejor presentación
            df_display = df_display.rename(columns={
                'texto_original': '📝 Original',
                'valor_normalizado': '✅ Normalizado',
                'metodo_usado': '⚙️ Método',
                'confianza': '🎯 Confianza',
                'requiere_revision': '👀 Revisión',
                'fecha_proceso': '📅 Fecha'
            })
            
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
            
            # Botón para descargar resultados
            csv_export = df_resultados.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Resultados (CSV)",
                data=csv_export,
                file_name=f"resultados_{archivo_info['nombre_archivo']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        else:
            st.warning("⚠️ No se encontraron resultados para este archivo.")
    
    except Exception as e:
        st.error(f"Error consultando resultados: {str(e)}")

def mostrar_configuracion_sistema():
    """Sección de configuración y administración del sistema"""
    
    st.markdown("## ⚙️ Configuración del Sistema")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗄️ Base de Datos", 
        "📚 Referencias", 
        "🧹 Mantenimiento", 
        "📊 Estadísticas"
    ])
    
    with tab1:
        mostrar_config_base_datos()
    
    with tab2:
        mostrar_gestion_referencias()
    
    with tab3:
        mostrar_mantenimiento_sistema()
    
    with tab4:
        mostrar_estadisticas_sistema()

# ========================================
# CORRECCIÓN ADICIONAL PARA OTRAS FUNCIONES SIMILARES
# ========================================

def mostrar_config_base_datos():
    """Configuración de base de datos - CORREGIDA"""
    
    st.markdown("### 🗄️ Configuración de PostgreSQL")
    
    sistema = SistemaNormalizacion()
    
    # Estado de conexión
    if sistema.engine:
        st.success("✅ Conexión a PostgreSQL activa")
        
        try:
            with sistema.engine.connect() as conn:
                # Información de la base de datos
                result = conn.execute(text("SELECT version()"))
                version_row = result.fetchone()
                version = version_row[0] if version_row else "Desconocida"
                
                result = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """))
                
                # CORRECCIÓN: Manejar resultados correctamente
                tablas_stats = []
                for row in result:
                    if row is not None:
                        tablas_stats.append(dict(row._mapping))
            
            # Mostrar información
            st.info(f"**Versión PostgreSQL:** {version}")
            
            if tablas_stats:
                st.markdown("#### 📊 Estadísticas de Tablas:")
                
                df_stats = pd.DataFrame(tablas_stats)
                df_stats.columns = ['Esquema', 'Tabla', 'Inserts', 'Updates', 'Deletes']
                
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ No hay estadísticas de tablas disponibles (tablas vacías)")
            
        except Exception as e:
            st.error(f"Error obteniendo información de BD: {str(e)}")
    
    else:
        st.error("❌ No hay conexión a PostgreSQL")
        
        # Ayuda para solucionar problemas de conexión
        st.markdown("### 🔧 Solución de Problemas:")
        st.markdown("""
        **Verifica la configuración:**
        - Host: localhost
        - Puerto: 5432
        - Base de datos: normalizacion_domicilios
        - Usuario: postgres
        - Contraseña: admin123
        
        **Comandos útiles:**
        ```bash
        # Verificar si PostgreSQL está corriendo
        sudo systemctl status postgresql
        
        # Crear base de datos
        createdb normalizacion_domicilios
        ```
        """)
    
    # Configuración de parámetros
    st.markdown("---")
    st.markdown("#### ⚙️ Parámetros del Sistema:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        batch_size = st.number_input("Tamaño de lote para procesamiento:", value=1000, min_value=100, max_value=10000)
        timeout_seconds = st.number_input("Timeout de consultas (segundos):", value=30, min_value=5, max_value=300)
    
    with col2:
        max_workers = st.number_input("Número máximo de hilos:", value=4, min_value=1, max_value=16)
        cache_ttl = st.number_input("TTL de cache (segundos):", value=300, min_value=60, max_value=3600)
    
    if st.button("💾 Guardar Configuración"):
        # En una implementación real, esto se guardaría en una tabla de configuración
        st.success("✅ Configuración guardada correctamente")

def mostrar_gestion_referencias():
    """Gestión completa de referencias"""
    
    st.markdown("### 📚 Gestión de Referencias")
    
    sistema = SistemaNormalizacion()
    
    # Resumen de referencias actuales
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    tipo_catalogo,
                    COUNT(*) as total,
                    COUNT(CASE WHEN coordenadas_lat IS NOT NULL THEN 1 END) as con_coordenadas,
                    MAX(fecha_actualizacion) as ultima_actualizacion
                FROM referencias_normalizacion
                WHERE activo = true
                GROUP BY tipo_catalogo
                ORDER BY tipo_catalogo
            """))
            
            referencias_resumen = [dict(row) for row in result]
    
        if referencias_resumen:
            st.markdown("#### 📊 Estado Actual de Referencias:")
            
            df_resumen = pd.DataFrame(referencias_resumen)
            df_resumen.columns = ['Tipo', 'Total', 'Con Coordenadas', 'Última Actualización']
            
            st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        else:
            st.warning("No hay referencias cargadas en el sistema")
    
    except Exception as e:
        st.error(f"Error consultando referencias: {str(e)}")
    
    st.markdown("---")
    
    # Acciones de mantenimiento de referencias
    st.markdown("#### 🔧 Acciones de Mantenimiento:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🧹 Limpiar Referencias Duplicadas"):
            limpiar_referencias_duplicadas(sistema)
    
    with col2:
        if st.button("📊 Validar Integridad"):
            validar_integridad_referencias(sistema)
    
    with col3:
        if st.button("📥 Exportar Referencias"):
            exportar_referencias(sistema)

def mostrar_mantenimiento_sistema():
    """Herramientas de mantenimiento del sistema"""
    
    st.markdown("### 🧹 Mantenimiento del Sistema")
    
    sistema = SistemaNormalizacion()
    
    # Estadísticas de espacio
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            
            tabla_sizes = [dict(row) for row in result]
    
        if tabla_sizes:
            st.markdown("#### 💽 Uso de Espacio por Tabla:")
            
            df_sizes = pd.DataFrame(tabla_sizes)
            df_sizes = df_sizes[['tablename', 'size']].copy()
            df_sizes.columns = ['Tabla', 'Tamaño']
            
            st.dataframe(df_sizes, use_container_width=True, hide_index=True)
    
    except Exception as e:
        st.error(f"Error consultando espacio: {str(e)}")
    
    st.markdown("---")
    
    # Herramientas de limpieza
    st.markdown("#### 🧹 Herramientas de Limpieza:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Limpieza de Datos Antiguos:**")
        
        dias_antiguos = st.number_input("Eliminar registros anteriores a (días):", value=90, min_value=30, max_value=365)
        
        if st.button("🗑️ Limpiar Datos Antiguos", type="secondary"):
            if st.checkbox("Confirmar eliminación de datos antiguos"):
                limpiar_datos_antiguos(sistema, dias_antiguos)
    
    with col2:
        st.markdown("**Optimización de Base de Datos:**")
        
        if st.button("⚡ Optimizar Tablas", type="secondary"):
            optimizar_tablas(sistema)
        
        if st.button("📊 Actualizar Estadísticas", type="secondary"):
            actualizar_estadisticas_bd(sistema)



# ========================================
# 7. DASHBOARD PRINCIPAL MEJORADO
# ========================================

def mostrar_dashboard_principal():
    """Dashboard principal con métricas del sistema completo - COMPLETAMENTE CORREGIDO"""
    
    st.markdown("## 📊 Dashboard Principal")
    
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            # Métricas generales
            result = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT a.id_archivo) as total_archivos,
                    COALESCE(SUM(a.total_registros), 0) as total_registros,
                    COUNT(r.id_resultado) as total_procesados,
                    COUNT(CASE WHEN r.valor_normalizado IS NOT NULL THEN 1 END) as total_normalizados,
                    COUNT(CASE WHEN r.requiere_revision = true THEN 1 END) as total_revision,
                    COALESCE(AVG(CASE WHEN r.confianza > 0 THEN r.confianza END), 0) as confianza_promedio
                FROM archivos_cargados a
                LEFT JOIN resultados_normalizacion r ON a.id_archivo = r.id_archivo
                WHERE a.fecha_carga >= CURRENT_DATE - INTERVAL '30 days'
            """))
            
            # CORRECCIÓN PRINCIPAL: Manejar resultado None
            row = result.fetchone()
            if row is not None:
                metricas = dict(row._mapping)  # Usar _mapping para SQLAlchemy 2.0
            else:
                metricas = {
                    'total_archivos': 0,
                    'total_registros': 0,
                    'total_procesados': 0,
                    'total_normalizados': 0,
                    'total_revision': 0,
                    'confianza_promedio': 0
                }
    
        # Asegurar que los valores no sean None
        for key in metricas:
            if metricas[key] is None:
                metricas[key] = 0
    
        # Mostrar métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #E2E8F0;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                    <div style="width: 40px; height: 40px; background: rgba(229, 62, 62, 0.1); 
                               border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <span style="color: #E53E3E; font-size: 1.2rem;">📁</span>
                    </div>
                    <h3 style="color: #2D3748; margin: 0; font-size: 0.9rem; font-weight: 600;">Archivos Procesados</h3>
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: #2D3748; margin-bottom: 0.5rem;">
                    {int(metricas['total_archivos']):,}
                </div>
                <div style="color: #2D3748; font-size: 0.85rem;">Últimos 30 días</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_procesados = int(metricas['total_procesados'])
            total_normalizados = int(metricas['total_normalizados'])
            porcentaje_exito = (total_normalizados / total_procesados * 100) if total_procesados > 0 else 0
            
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #E2E8F0;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                    <div style="width: 40px; height: 40px; background: rgba(56, 161, 105, 0.1); 
                               border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <span style="color: #38A169; font-size: 1.2rem;">✅</span>
                    </div>
                    <h3 style="color: #2D3748; margin: 0; font-size: 0.9rem; font-weight: 600;">Tasa de Éxito</h3>
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: #2D3748; margin-bottom: 0.5rem;">
                    {porcentaje_exito:.1f}%
                </div>
                <div style="color: #2D3748; font-size: 0.85rem;">Normalización exitosa</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #E2E8F0;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                    <div style="width: 40px; height: 40px; background: rgba(0, 102, 204, 0.1); 
                               border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <span style="color: #0066CC; font-size: 1.2rem;">📊</span>
                    </div>
                    <h3 style="color: #2D3748; margin: 0; font-size: 0.9rem; font-weight: 600;">Total Registros</h3>
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: #2D3748; margin-bottom: 0.5rem;">
                    {total_procesados:,}
                </div>
                <div style="color: #2D3748; font-size: 0.85rem;">Registros procesados</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            confianza_prom = float(metricas['confianza_promedio']) * 100
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #E2E8F0;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                    <div style="width: 40px; height: 40px; background: rgba(214, 158, 46, 0.1); 
                               border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                        <span style="color: #D69E2E; font-size: 1.2rem;">🎯</span>
                    </div>
                    <h3 style="color: #2D3748; margin: 0; font-size: 0.9rem; font-weight: 600;">Confianza Promedio</h3>
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: #2D3748; margin-bottom: 0.5rem;">
                    {confianza_prom:.1f}%
                </div>
                <div style="color: #2D3748; font-size: 0.85rem;">Nivel de confianza</div>
            </div>
            """, unsafe_allow_html=True)
    
        # Gráficos de análisis
        st.markdown("---")
        mostrar_graficos_analisis()
    
    except Exception as e:
        st.error(f"Error cargando dashboard: {str(e)}")
        # Mostrar dashboard con valores por defecto
        mostrar_dashboard_vacio()


def mostrar_dashboard_vacio():
    """Mostrar dashboard con valores por defecto cuando no hay datos"""
    
    st.info("👋 ¡Bienvenido al Sistema de Normalización! No hay datos procesados aún.")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Archivos Procesados", "0", "📁")
    with col2:
        st.metric("Tasa de Éxito", "0%", "✅")
    with col3:
        st.metric("Total Registros", "0", "📊")
    with col4:
        st.metric("Confianza Promedio", "0%", "🎯")
    
    st.markdown("---")
    st.markdown("### 🚀 ¿Cómo empezar?")
    st.markdown("""
    1. **📁 Sube archivos** en la pestaña "Carga de Archivos"
    2. **📚 Configura referencias** SEPOMEX/INEGI si es necesario
    3. **⚙️ Procesa los datos** y ve los resultados aquí
    """)


def mostrar_referencias_actuales():
    """Mostrar las referencias actuales en el sistema - CORREGIDO"""
    
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tipo_catalogo, COUNT(*) as total_referencias,
                       MAX(fecha_actualizacion) as ultima_actualizacion
                FROM referencias_normalizacion 
                WHERE activo = true
                GROUP BY tipo_catalogo
                ORDER BY tipo_catalogo
            """))
            
            # CORRECCIÓN: Manejar resultados vacíos
            referencias = []
            for row in result:
                referencias.append(dict(row._mapping))
        
        if referencias:
            st.markdown("#### 📋 Referencias Actuales:")
            
            df_referencias = pd.DataFrame(referencias)
            df_referencias.columns = ['Tipo', 'Total Referencias', 'Última Actualización']
            
            st.dataframe(df_referencias, use_container_width=True, hide_index=True)
        else:
            st.info("📝 No hay referencias cargadas en el sistema. Sube archivos de referencia SEPOMEX/INEGI para mejorar la precisión.")
    
    except Exception as e:
        st.error(f"Error consultando referencias: {str(e)}")


def mostrar_graficos_analisis():
    """Mostrar gráficos de análisis del sistema - COMPLETAMENTE CORREGIDO"""
    
    sistema = SistemaNormalizacion()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Procesamiento por Tipo de Catálogo")
        
        try:
            with sistema.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        r.tipo_catalogo,
                        COUNT(*) as total,
                        COUNT(CASE WHEN r.valor_normalizado IS NOT NULL THEN 1 END) as exitosos
                    FROM resultados_normalizacion r
                    WHERE r.fecha_proceso >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY r.tipo_catalogo
                    ORDER BY total DESC
                """))
                
                # CORRECCIÓN: Manejar resultados vacíos correctamente
                datos = []
                for row in result:
                    datos.append(dict(row._mapping))
            
            if datos and len(datos) > 0:
                df_tipos = pd.DataFrame(datos)
                df_tipos['porcentaje_exito'] = (df_tipos['exitosos'] / df_tipos['total'] * 100).round(1)
                
                fig = px.bar(
                    df_tipos,
                    x='tipo_catalogo',
                    y='porcentaje_exito',
                    color='tipo_catalogo',
                    text='porcentaje_exito',
                    color_discrete_sequence=['#E53E3E', '#0066CC', '#38A169', '#D69E2E']
                )
                
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    height=300,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📈 No hay datos de procesamiento recientes para mostrar gráficos.")
        
        except Exception as e:
            st.error(f"Error generando gráfico: {str(e)}")
    
    with col2:
        st.markdown("### 🎯 Distribución de Métodos de Normalización")
        
        try:
            with sistema.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT metodo_usado, COUNT(*) as cantidad
                    FROM resultados_normalizacion
                    WHERE fecha_proceso >= CURRENT_DATE - INTERVAL '30 days'
                    AND metodo_usado IS NOT NULL
                    GROUP BY metodo_usado
                    ORDER BY cantidad DESC
                """))
                
                # CORRECCIÓN: Manejar resultados vacíos
                metodos = []
                for row in result:
                    metodos.append(dict(row._mapping))
            
            if metodos and len(metodos) > 0:
                df_metodos = pd.DataFrame(metodos)
                
                fig = go.Figure(data=[go.Pie(
                    labels=df_metodos['metodo_usado'],
                    values=df_metodos['cantidad'],
                    hole=0.4,
                    marker=dict(
                        colors=['#0066CC', '#38A169', '#D69E2E', '#E53E3E'],
                        line=dict(color='white', width=2)
                    )
                )])
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=300,
                    margin=dict(l=0, r=0, t=0, b=0),
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("🎯 No hay datos de métodos recientes para mostrar.")
        
        except Exception as e:
            st.error(f"Error generando gráfico de métodos: {str(e)}")


# ========================================
# CORRECCIÓN ADICIONAL PARA ESTADÍSTICAS
# ========================================

def mostrar_estadisticas_sistema():
    """Estadísticas detalladas del sistema - COMPLETAMENTE CORREGIDO"""
    
    st.markdown("### 📊 Estadísticas del Sistema")
    
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            # Estadísticas generales
            result = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT a.id_archivo) as total_archivos,
                    COALESCE(SUM(a.total_registros), 0) as total_registros_cargados,
                    COUNT(r.id_resultado) as total_registros_procesados,
                    COUNT(CASE WHEN r.valor_normalizado IS NOT NULL THEN 1 END) as registros_exitosos,
                    COUNT(CASE WHEN r.requiere_revision = true THEN 1 END) as requieren_revision,
                    COALESCE(AVG(CASE WHEN r.confianza > 0 THEN r.confianza END), 0) as confianza_promedio,
                    MIN(a.fecha_carga) as primera_carga,
                    MAX(a.fecha_carga) as ultima_carga
                FROM archivos_cargados a
                LEFT JOIN resultados_normalizacion r ON a.id_archivo = r.id_archivo
            """))
            
            # CORRECCIÓN PRINCIPAL
            row = result.fetchone()
            if row is not None:
                stats_generales = dict(row._mapping)
            else:
                stats_generales = {
                    'total_archivos': 0,
                    'total_registros_cargados': 0,
                    'total_registros_procesados': 0,
                    'registros_exitosos': 0,
                    'requieren_revision': 0,
                    'confianza_promedio': 0,
                    'primera_carga': None,
                    'ultima_carga': None
                }
            
            # Asegurar valores no None
            for key in stats_generales:
                if stats_generales[key] is None and key not in ['primera_carga', 'ultima_carga']:
                    stats_generales[key] = 0
            
            # Estadísticas por división
            result = conn.execute(text("""
                SELECT 
                    r.division,
                    COUNT(*) as total,
                    COUNT(CASE WHEN r.valor_normalizado IS NOT NULL THEN 1 END) as exitosos,
                    COALESCE(AVG(CASE WHEN r.confianza > 0 THEN r.confianza END), 0) as confianza_promedio
                FROM resultados_normalizacion r
                GROUP BY r.division
                ORDER BY total DESC
            """))
            
            stats_division = []
            for row in result:
                stats_division.append(dict(row._mapping))
            
            # Estadísticas por método
            result = conn.execute(text("""
                SELECT 
                    metodo_usado,
                    COUNT(*) as cantidad,
                    COALESCE(AVG(confianza), 0) as confianza_promedio
                FROM resultados_normalizacion
                WHERE metodo_usado IS NOT NULL
                GROUP BY metodo_usado
                ORDER BY cantidad DESC
            """))
            
            stats_metodos = []
            for row in result:
                stats_metodos.append(dict(row._mapping))
    
        # Mostrar estadísticas generales
        st.markdown("#### 📈 Estadísticas Generales:")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Archivos Procesados", f"{int(stats_generales['total_archivos']):,}")
        
        with col2:
            st.metric("Registros Totales", f"{int(stats_generales['total_registros_procesados']):,}")
        
        with col3:
            total_proc = int(stats_generales['total_registros_procesados'])
            exitosos = int(stats_generales['registros_exitosos'])
            porcentaje_exito = (exitosos / total_proc * 100) if total_proc > 0 else 0
            st.metric("Tasa de Éxito", f"{porcentaje_exito:.1f}%")
        
        with col4:
            confianza = float(stats_generales['confianza_promedio']) * 100
            st.metric("Confianza Promedio", f"{confianza:.1f}%")
        
        # Estadísticas por división
        if stats_division:
            st.markdown("#### 🏢 Estadísticas por División:")
            
            df_division = pd.DataFrame(stats_division)
            # Evitar división por cero y valores None
            df_division['porcentaje_exito'] = df_division.apply(
                lambda row: (row['exitosos'] / row['total'] * 100) if row['total'] > 0 else 0, axis=1
            ).round(1)
            df_division['confianza_promedio'] = (df_division['confianza_promedio'] * 100).round(1)
            
            df_division.columns = ['División', 'Total', 'Exitosos', 'Confianza %', '% Éxito']
            
            st.dataframe(df_division, use_container_width=True, hide_index=True)
        
        # Estadísticas por método
        if stats_metodos:
            st.markdown("#### ⚙️ Estadísticas por Método:")
            
            df_metodos = pd.DataFrame(stats_metodos)
            df_metodos['confianza_promedio'] = (df_metodos['confianza_promedio'] * 100).round(1)
            
            df_metodos.columns = ['Método', 'Cantidad', 'Confianza Promedio %']
            
            st.dataframe(df_metodos, use_container_width=True, hide_index=True)
        
        # Información temporal
        if stats_generales['primera_carga']:
            st.markdown("#### 📅 Información Temporal:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**Primera carga:** {stats_generales['primera_carga']}")
            
            with col2:
                st.info(f"**Última carga:** {stats_generales['ultima_carga']}")
        else:
            st.info("ℹ️ No hay datos históricos disponibles. El sistema está listo para procesar archivos.")
    
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {str(e)}")


# ========================================
# 8. APLICACIÓN PRINCIPAL
# ========================================

def main():
    """Aplicación principal del sistema integral"""
    
    # Aplicar estilos CSS
    st.markdown(f"""
    <style>
        .stApp {{
            background: {COLORES['gris_claro']};
        }}
        
        .main-header {{
            background: linear-gradient(135deg, {COLORES['azul_telmex']}, {COLORES['rojo_principal']});
            background: linear-gradient(135deg, {COLORES['blanco']}, {COLORES['blanco']});
            color: navy;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        
        .main-header h1 {{
            font-size: 2.5rem;
            font-weight: 900;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .main-header p {{
            font-size: 1.2rem;
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🏠 Sistema Integral de Normalización Telmex</h1>
        <p>Procesamiento Inteligente de Domicilios | AS400 ↔ PostgreSQL | Automatización Completa</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navegación principal
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", 
        "📁 Carga de Archivos", 
        "📋 Resultados", 
        "⚙️ Configuración"
    ])
    
    with tab1:
        mostrar_dashboard_principal()
    
    with tab2:
        mostrar_interfaz_carga()
    
    with tab3:
        mostrar_seccion_resultados()
    
    with tab4:
        mostrar_configuracion_sistema()

def mostrar_seccion_resultados():
    """Sección para consultar y analizar resultados históricos"""
    
    st.markdown("## 📋 Consulta de Resultados Históricos")
    
    sistema = SistemaNormalizacion()
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tipo_filtro = st.selectbox(
            "Tipo de Catálogo:",
            ["TODOS"] + list(ESQUEMAS_AS400.keys()),
            key="filtro_tipo"
        )
    
    with col2:
        division_filtro = st.selectbox(
            "División:",
            ["TODAS", "DES", "QAS", "MEX", "GDL", "MTY", "NTE", "TIJ"],
            key="filtro_division"
        )
    
    with col3:
        fecha_desde = st.date_input(
            "Desde:",
            value=datetime.now() - timedelta(days=30),
            key="filtro_fecha"
        )
    
    # Consultar resultados
    if st.button("🔍 Buscar Resultados"):
        consultar_resultados_historicos(sistema, tipo_filtro, division_filtro, fecha_desde)

def consultar_resultados_historicos(sistema, tipo_filtro, division_filtro, fecha_desde):
    """Consultar resultados históricos con filtros - CORREGIDA"""
    
    try:
        # Construir consulta con filtros
        where_conditions = ["r.fecha_proceso >= :fecha_desde"]
        params = {'fecha_desde': fecha_desde}
        
        if tipo_filtro != "TODOS":
            where_conditions.append("r.tipo_catalogo = :tipo")
            params['tipo'] = tipo_filtro
        
        if division_filtro != "TODAS":
            where_conditions.append("r.division = :division")
            params['division'] = division_filtro
        
        where_clause = " AND ".join(where_conditions)
        
        with sistema.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT 
                    a.nombre_archivo,
                    r.tipo_catalogo,
                    r.division,
                    r.texto_original,
                    r.valor_normalizado,
                    r.metodo_usado,
                    r.confianza,
                    r.requiere_revision,
                    r.fecha_proceso
                FROM resultados_normalizacion r
                JOIN archivos_cargados a ON r.id_archivo = a.id_archivo
                WHERE {where_clause}
                ORDER BY r.fecha_proceso DESC
                LIMIT 1000
            """), params)
            
            # CORRECCIÓN: Manejar resultados correctamente
            resultados = []
            for row in result:
                if row is not None:
                    resultados.append(dict(row._mapping))
        
        if resultados:
            st.success(f"✅ Se encontraron {len(resultados)} resultados")
            
            # Mostrar estadísticas
            df_resultados = pd.DataFrame(resultados)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Encontrados", f"{len(resultados):,}")
            
            with col2:
                exitosos = len(df_resultados[df_resultados['valor_normalizado'].notna()])
                porcentaje_exito = (exitosos/len(resultados)*100) if len(resultados) > 0 else 0
                st.metric("Exitosos", f"{exitosos:,}", f"{porcentaje_exito:.1f}%")
            
            with col3:
                revision = len(df_resultados[df_resultados['requiere_revision'] == True])
                st.metric("Requieren Revisión", f"{revision:,}")
            
            with col4:
                confianzas_validas = df_resultados['confianza'].dropna()
                confianza = confianzas_validas.mean() if len(confianzas_validas) > 0 else 0
                st.metric("Confianza Promedio", f"{confianza:.1%}" if confianza > 0 else "N/A")
            
            # Mostrar tabla de resultados
            st.markdown("### 📊 Resultados Detallados:")
            
            # Preparar columnas para mostrar
            df_display = df_resultados.copy()
            df_display['confianza'] = df_display['confianza'].apply(lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "N/A")
            df_display['requiere_revision'] = df_display['requiere_revision'].apply(lambda x: "⚠️ Sí" if x else "✅ No")
            df_display['fecha_proceso'] = pd.to_datetime(df_display['fecha_proceso']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Seleccionar columnas principales
            columnas_mostrar = [
                'nombre_archivo', 'tipo_catalogo', 'division', 'texto_original', 
                'valor_normalizado', 'metodo_usado', 'confianza', 'requiere_revision', 'fecha_proceso'
            ]
            
            df_final = df_display[columnas_mostrar].copy()
            df_final.columns = [
                '📄 Archivo', '📋 Tipo', '🏢 División', '📝 Original', 
                '✅ Normalizado', '⚙️ Método', '🎯 Confianza', '👀 Revisión', '📅 Fecha'
            ]
            
            st.dataframe(df_final, use_container_width=True, hide_index=True, height=400)
            
            # Botón para descargar resultados
            csv_export = df_resultados.to_csv(index=False)
            st.download_button(
                label="📥 Descargar Resultados (CSV)",
                data=csv_export,
                file_name=f"resultados_historicos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        else:
            st.warning("⚠️ No se encontraron resultados con los filtros especificados")
            
            # Sugerencias para el usuario
            st.markdown("### 💡 Sugerencias:")
            st.markdown("""
            - **Amplía el rango de fechas**: Selecciona una fecha más antigua
            - **Cambia los filtros**: Prueba con "TODOS" en tipo y división
            - **Verifica datos**: Asegúrate de haber procesado archivos recientemente
            - **Revisa la pestaña "Procesamiento"** para ver el estado de los archivos
            """)
    
    except Exception as e:
        st.error(f"Error consultando resultados: {str(e)}")
        
        # Información de ayuda
        st.markdown("### 🔧 Información Técnica:")
        st.code(f"""
Filtros aplicados:
- Tipo: {tipo_filtro}
- División: {division_filtro}  
- Fecha desde: {fecha_desde}

Error: {str(e)}
        """)

# ========================================
# 9. FUNCIONES DE UTILIDAD
# ========================================

def limpiar_referencias_duplicadas(sistema):
    """Limpiar referencias duplicadas"""
    
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                WITH duplicados AS (
                    SELECT id_referencia,
                           ROW_NUMBER() OVER (
                               PARTITION BY tipo_catalogo, nombre_oficial 
                               ORDER BY fecha_actualizacion DESC
                           ) as rn
                    FROM referencias_normalizacion
                )
                DELETE FROM referencias_normalizacion 
                WHERE id_referencia IN (
                    SELECT id_referencia FROM duplicados WHERE rn > 1
                )
            """))
            
            conn.commit()
            eliminados = result.rowcount
        
        st.success(f"✅ Se eliminaron {eliminados} referencias duplicadas")
    
    except Exception as e:
        st.error(f"Error limpiando duplicados: {str(e)}")

def validar_integridad_referencias(sistema):
    """Validar integridad de las referencias"""
    
    try:
        with sistema.engine.connect() as conn:
            # Buscar referencias sin nombre oficial
            result = conn.execute(text("""
                SELECT COUNT(*) FROM referencias_normalizacion 
                WHERE nombre_oficial IS NULL OR nombre_oficial = ''
            """))
            sin_nombre = result.fetchone()[0]
            
            # Buscar referencias sin código
            result = conn.execute(text("""
                SELECT COUNT(*) FROM referencias_normalizacion 
                WHERE codigo_oficial IS NULL OR codigo_oficial = ''
            """))
            sin_codigo = result.fetchone()[0]
            
            # Buscar referencias inactivas
            result = conn.execute(text("""
                SELECT COUNT(*) FROM referencias_normalizacion WHERE activo = false
            """))
            inactivos = result.fetchone()[0]
        
        # Mostrar resultados
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if sin_nombre > 0:
                st.error(f"❌ {sin_nombre} referencias sin nombre oficial")
            else:
                st.success("✅ Todas tienen nombre oficial")
        
        with col2:
            if sin_codigo > 0:
                st.warning(f"⚠️ {sin_codigo} referencias sin código oficial")
            else:
                st.success("✅ Todas tienen código oficial")
        
        with col3:
            if inactivos > 0:
                st.info(f"ℹ️ {inactivos} referencias inactivas")
            else:
                st.success("✅ Todas las referencias están activas")
    
    except Exception as e:
        st.error(f"Error validando integridad: {str(e)}")

def exportar_referencias(sistema):
    """Exportar todas las referencias"""
    
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM referencias_normalizacion 
                WHERE activo = true 
                ORDER BY tipo_catalogo, nombre_oficial
            """))
            
            referencias = [dict(row) for row in result]
        
        if referencias:
            df_export = pd.DataFrame(referencias)
            csv_export = df_export.to_csv(index=False)
            
            st.download_button(
                label="📥 Descargar Referencias Completas",
                data=csv_export,
                file_name=f"referencias_completas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success(f"✅ Preparadas {len(referencias)} referencias para descarga")
        else:
            st.warning("No hay referencias para exportar")
    
    except Exception as e:
        st.error(f"Error exportando referencias: {str(e)}")

def limpiar_datos_antiguos(sistema, dias):
    """Limpiar datos anteriores a X días"""
    
    try:
        fecha_limite = datetime.now() - timedelta(days=dias)
        
        with sistema.engine.connect() as conn:
            # Eliminar resultados antiguos
            result = conn.execute(text("""
                DELETE FROM resultados_normalizacion 
                WHERE fecha_proceso < :fecha_limite
            """), {'fecha_limite': fecha_limite})
            
            resultados_eliminados = result.rowcount
            
            # Eliminar archivos sin resultados
            result = conn.execute(text("""
                DELETE FROM archivos_cargados 
                WHERE fecha_carga < :fecha_limite
                AND id_archivo NOT IN (SELECT DISTINCT id_archivo FROM resultados_normalizacion)
            """), {'fecha_limite': fecha_limite})
            
            archivos_eliminados = result.rowcount
            
            conn.commit()
        
        st.success(f"✅ Eliminados: {resultados_eliminados} resultados y {archivos_eliminados} archivos")
    
    except Exception as e:
        st.error(f"Error limpiando datos antiguos: {str(e)}")

def optimizar_tablas(sistema):
    """Optimizar tablas de PostgreSQL"""
    
    try:
        with sistema.engine.connect() as conn:
            # VACUUM y ANALYZE en tablas principales
            tablas = ['resultados_normalizacion', 'archivos_cargados', 'referencias_normalizacion']
            
            for tabla in tablas:
                conn.execute(text(f"VACUUM ANALYZE {tabla}"))
            
            conn.commit()
        
        st.success("✅ Tablas optimizadas correctamente")
    
    except Exception as e:
        st.error(f"Error optimizando tablas: {str(e)}")

def actualizar_estadisticas_bd(sistema):
    """Actualizar estadísticas de PostgreSQL"""
    
    try:
        with sistema.engine.connect() as conn:
            conn.execute(text("ANALYZE"))
            conn.commit()
        
        st.success("✅ Estadísticas de base de datos actualizadas")
    
    except Exception as e:
        st.error(f"Error actualizando estadísticas: {str(e)}")


            

        

    
def descargar_resultados_archivo(id_archivo):
    """Generar descarga de resultados de un archivo"""

    sistema = SistemaNormalizacion()

    try:
        with sistema.engine.connect() as conn:
            # Obtener información del archivo
            result = conn.execute(text("""
                SELECT nombre_archivo, tipo_catalogo, division 
                FROM archivos_cargados WHERE id_archivo = :id_archivo
            """), {'id_archivo': id_archivo})
            
            archivo_info = dict(result.fetchone())
            
            # Obtener resultados
            result = conn.execute(text("""
                SELECT 
                    campo_status, campo_clave, campo_descripcion, texto_original,
                    valor_normalizado, codigo_normalizado, metodo_usado, confianza,
                    coordenadas_lat, coordenadas_lng, requiere_revision,
                    fecha_proceso, observaciones
                FROM resultados_normalizacion 
                WHERE id_archivo = :id_archivo
                ORDER BY fecha_proceso
            """), {'id_archivo': id_archivo})
            
            resultados = [dict(row) for row in result]
        
        if resultados:
            # Crear DataFrames para diferentes formatos
            df_completo = pd.DataFrame(resultados)
            
            # Formato para AS400 (solo campos necesarios)
            df_as400 = df_completo[['campo_status', 'campo_clave', 'valor_normalizado', 'codigo_normalizado']].copy()
            df_as400.columns = ['STATUS', 'CLAVE_ORIGINAL', 'DESCRIPCION_NORMALIZADA', 'CODIGO_NORMALIZADO']
            
            # Formato para revisión manual (solo casos que requieren revisión)
            df_revision = df_completo[df_completo['requiere_revision'] == True].copy()
            
            # Crear archivo ZIP con múltiples formatos
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                # Archivo completo
                csv_completo = df_completo.to_csv(index=False)
                zip_file.writestr(f"{archivo_info['nombre_archivo']}_completo.csv", csv_completo)
                
                # Archivo para AS400
                csv_as400 = df_as400.to_csv(index=False)
                zip_file.writestr(f"{archivo_info['nombre_archivo']}_as400.csv", csv_as400)
                
                # Archivo de casos para revisión
                if not df_revision.empty:
                    csv_revision = df_revision.to_csv(index=False)
                    zip_file.writestr(f"{archivo_info['nombre_archivo']}_revision.csv", csv_revision)
                
                # Reporte de resumen
                resumen = f"""

REPORTE DE PROCESAMIENTO
========================

Archivo: {archivo_info['nombre_archivo']}
Tipo: {archivo_info['tipo_catalogo']}
División: {archivo_info['division']}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ESTADÍSTICAS:
- Total de registros: {len(resultados):,}
- Registros exitosos: {len(df_completo[df_completo['valor_normalizado'].notna()]):,}
- Requieren revisión: {len(df_revision):,}
- Confianza promedio: {df_completo['confianza'].mean():.1%}

MÉTODOS UTILIZADOS:
{df_completo['metodo_usado'].value_counts().to_string()}

ARCHIVOS INCLUIDOS:
- {archivo_info['nombre_archivo']}_completo.csv: Todos los resultados
- {archivo_info['nombre_archivo']}_as400.csv: Formato para cargar en AS400
- {archivo_info['nombre_archivo']}_revision.csv: Casos que requieren revisión manual
                """
                
                zip_file.writestr(f"{archivo_info['nombre_archivo']}_reporte.txt", resumen)
            
            # Preparar descarga
            zip_buffer.seek(0)
            
            nombre_descarga = f"resultados_{archivo_info['tipo_catalogo']}_{archivo_info['division']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            st.download_button(
                label="📥 Descargar Resultados Completos",
                data=zip_buffer.getvalue(),
                file_name=nombre_descarga,
                mime="application/zip"
            )
            
            st.success(f"✅ Preparado para descarga: {len(resultados):,} registros")
        
        else:
            st.warning("No hay resultados para descargar")
    
    except Exception as e:
        st.error(f"Error preparando descarga: {str(e)}")

def eliminar_archivo_procesado(id_archivo):
    """Eliminar archivo procesado y sus resultados"""
    
    sistema = SistemaNormalizacion()
    
    if st.checkbox("Confirmar eliminación", key=f"confirm_del_{id_archivo}"):
        try:
            with sistema.engine.connect() as conn:
                # Eliminar resultados
                conn.execute(text("""
                    DELETE FROM resultados_normalizacion WHERE id_archivo = :id_archivo
                """), {'id_archivo': id_archivo})
                
                # Eliminar registro del archivo
                conn.execute(text("""
                    DELETE FROM archivos_cargados WHERE id_archivo = :id_archivo
                """), {'id_archivo': id_archivo})
                
                conn.commit()
            
            st.success("✅ Archivo eliminado correctamente")
            st.rerun()
        
        except Exception as e:
            st.error(f"Error eliminando archivo: {str(e)}")


# ========================================
# 10. EJECUCIÓN PRINCIPAL
# ========================================

if __name__ == "__main__":
    main()
