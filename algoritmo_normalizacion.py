# ========================================
# ARCHIVO: algoritmo_normalizacion.py
# EL CEREBRO DE NUESTRO SISTEMA
# ========================================

"""
💡 ¿QUÉ HACE ESTE ARCHIVO?
Este es el corazón de nuestro proyecto. Aquí vive el "cerebro" que:
- Lee los datos "sucios" de AS400
- Los compara con los datos "limpios" de SEPOMEX  
- Encuentra las coincidencias usando inteligencia artificial gratuita
- Nos dice qué tan seguro está de cada coincidencia

Es como tener un detective súper inteligente que encuentra pistas
para resolver el misterio de "¿a qué estado se refiere cada registro?"
"""

import pandas as pd
import os
from fuzzywuzzy import fuzz, process
import re
import unicodedata
from datetime import datetime

print("🧠 CARGANDO EL CEREBRO DEL SISTEMA...")

# ========================================
# 1. DICCIONARIO DE EQUIVALENCIAS
# ========================================

# 💡 Estas son "pistas" que le damos al detective
# Son abreviaciones y nombres alternativos comunes en México
EQUIVALENCIAS_ESTADOS = {
    # Casos comunes del DF/CDMX
    'DF': 'CIUDAD DE MÉXICO',
    'DISTRITO FEDERAL': 'CIUDAD DE MÉXICO', 
    'D.F.': 'CIUDAD DE MÉXICO',
    'CDMX': 'CIUDAD DE MÉXICO',
    'MEXICO DF': 'CIUDAD DE MÉXICO',
    
    # Estado de México
    'EDO DE MEX': 'MÉXICO',
    'ESTADO DE MEXICO': 'MÉXICO',
    'EDO MEX': 'MÉXICO',
    'ESTADO DE MÉXICO': 'MÉXICO',
    
    # Abreviaciones comunes
    'BC': 'BAJA CALIFORNIA',
    'BCS': 'BAJA CALIFORNIA SUR',
    'COAH': 'COAHUILA DE ZARAGOZA',
    'COAHUILA': 'COAHUILA DE ZARAGOZA',
    'CHIS': 'CHIAPAS',
    'CHIH': 'CHIHUAHUA',
    'GTO': 'GUANAJUATO',
    'GRO': 'GUERRERO',
    'HGO': 'HIDALGO',
    'JAL': 'JALISCO',
    'MICH': 'MICHOACÁN DE OCAMPO',
    'MICHOACAN': 'MICHOACÁN DE OCAMPO',
    'MOR': 'MORELOS',
    'NAY': 'NAYARIT',
    'NL': 'NUEVO LEÓN',
    'NUEVO LEON': 'NUEVO LEÓN',
    'OAX': 'OAXACA',
    'PUE': 'PUEBLA',
    'QRO': 'QUERÉTARO',
    'QUERETARO': 'QUERÉTARO',
    'QROO': 'QUINTANA ROO',
    'SLP': 'SAN LUIS POTOSÍ',
    'SAN LUIS POTOSI': 'SAN LUIS POTOSÍ',
    'SIN': 'SINALOA',
    'SON': 'SONORA',
    'TAB': 'TABASCO',
    'TAMPS': 'TAMAULIPAS',
    'TLAX': 'TLAXCALA',
    'VER': 'VERACRUZ DE IGNACIO DE LA LLAVE',
    'VERACRUZ': 'VERACRUZ DE IGNACIO DE LA LLAVE',
    'YUC': 'YUCATÁN',
    'YUCATAN': 'YUCATÁN',
    'ZAC': 'ZACATECAS'
}

# ========================================
# 2. FUNCIÓN PARA LIMPIAR TEXTO
# ========================================

def limpiar_texto(texto):
    """
    💡 Esta función es como un "lavado de datos"
    Toma un texto sucio y lo deja limpio para comparar
    
    Ejemplo:
    "  distrito  FEDERAL  " → "DISTRITO FEDERAL"
    "Michoacán" → "MICHOACAN"
    """
    
    if not isinstance(texto, str) or texto is None:
        return ""
    
    # Paso 1: Convertir a mayúsculas y quitar espacios extra
    texto = texto.upper().strip()
    
    # Paso 2: Quitar acentos (á → a, é → e, etc.)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
    
    # Paso 3: Quitar caracteres especiales y espacios múltiples
    texto = re.sub(r'[^\w\s]', ' ', texto)  # Cambiar símbolos por espacios
    texto = re.sub(r'\s+', ' ', texto)      # Espacios múltiples → un espacio
    texto = texto.strip()                   # Quitar espacios al inicio/final
    
    return texto

# ========================================
# 3. DETECTIVE NIVEL 1 - COINCIDENCIA EXACTA
# ========================================

def detective_exacto(texto_as400, df_sepomex):
    """
    💡 El detective más estricto - busca coincidencias perfectas
    
    ¿Cómo funciona?
    1. Limpia el texto de AS400
    2. Busca en nuestro diccionario de equivalencias
    3. Si no está ahí, busca en SEPOMEX
    4. Solo acepta coincidencias 100% exactas
    """
    
    texto_limpio = limpiar_texto(texto_as400)
    
    if not texto_limpio:
        return None, 0.0, "Texto vacío"
    
    # Buscar en equivalencias conocidas
    if texto_limpio in EQUIVALENCIAS_ESTADOS:
        estado_encontrado = EQUIVALENCIAS_ESTADOS[texto_limpio]
        return estado_encontrado, 1.0, f"Equivalencia: {texto_limpio} → {estado_encontrado}"
    
    # Buscar en catálogo SEPOMEX
    for _, row in df_sepomex.iterrows():
        nombre_sepomex = limpiar_texto(row['nombre_oficial'])
        if texto_limpio == nombre_sepomex:
            return row['nombre_oficial'], 1.0, f"Match exacto con SEPOMEX"
    
    return None, 0.0, "Sin coincidencia exacta"

# ========================================
# 4. DETECTIVE NIVEL 2 - COINCIDENCIA FUZZY
# ========================================

def detective_fuzzy(texto_as400, df_sepomex, umbral_minimo=60):
    """
    💡 El detective flexible - encuentra coincidencias parecidas
    
    ¿Cómo funciona?
    1. Compara el texto con todos los estados de SEPOMEX
    2. Usa algoritmos de "similitud de texto"
    3. Calcula un porcentaje de parecido
    4. Si es mayor al umbral, lo acepta
    
    Ejemplo:
    "MICHOACAN" vs "MICHOACÁN DE OCAMPO" = 85% similar ✅
    "BASURA123" vs "MICHOACÁN DE OCAMPO" = 15% similar ❌
    """
    
    texto_limpio = limpiar_texto(texto_as400)
    
    if not texto_limpio:
        return None, 0.0, "Texto vacío"
    
    # Crear lista de estados para comparar
    estados_sepomex = df_sepomex['nombre_oficial'].tolist()
    
    # Buscar la mejor coincidencia
    mejor_match = process.extractOne(
        texto_limpio, 
        estados_sepomex,
        scorer=fuzz.token_sort_ratio  # Algoritmo que ignora orden de palabras
    )
    
    if mejor_match and mejor_match[1] >= umbral_minimo:
        estado_encontrado = mejor_match[0]
        confianza = mejor_match[1] / 100.0  # Convertir % a decimal
        explicacion = f"Fuzzy match: '{texto_limpio}' ≈ '{estado_encontrado}' ({mejor_match[1]}%)"
        return estado_encontrado, confianza, explicacion
    
    return None, 0.0, f"Mejor match: {mejor_match[1] if mejor_match else 0}% (muy bajo)"

# ========================================
# 5. DETECTIVE NIVEL 3 - COINCIDENCIA SEMÁNTICA
# ========================================

def detective_semantico(texto_as400, df_sepomex):
    """
    💡 El detective inteligente - entiende el significado
    
    ¿Cómo funciona?
    1. Busca palabras clave dentro del texto
    2. Usa reglas específicas para México
    3. Entiende context como "FEDERAL" = Ciudad de México
    """
    
    texto_limpio = limpiar_texto(texto_as400)
    
    # Reglas semánticas específicas para México
    reglas = {
        'FEDERAL': 'CIUDAD DE MÉXICO',
        'CAPITAL': 'CIUDAD DE MÉXICO', 
        'BAJA CALIFORNIA NORTE': 'BAJA CALIFORNIA',
        'BAJA CALIFORNIA PENINSULA': 'BAJA CALIFORNIA',
        'LEON': 'NUEVO LEÓN',
        'POTOSI': 'SAN LUIS POTOSÍ',
        'VERACRUZ LLAVE': 'VERACRUZ DE IGNACIO DE LA LLAVE'
    }
    
    for patron, estado_oficial in reglas.items():
        if patron in texto_limpio:
            return estado_oficial, 0.75, f"Regla semántica: '{patron}' → {estado_oficial}"
    
    return None, 0.0, "Sin regla semántica aplicable"

# ========================================
# 6. EL DETECTIVE PRINCIPAL - COORDINA TODO
# ========================================

def detective_principal(texto_as400, df_sepomex):
    """
    💡 Este es el jefe de detectives
    Coordina a todos los demás y decide el resultado final
    
    Proceso:
    1. Intenta Detective Exacto (más confiable)
    2. Si falla, intenta Detective Fuzzy  
    3. Si falla, intenta Detective Semántico
    4. Clasifica el resultado según la confianza
    """
    
    resultado = {
        'texto_original': texto_as400,
        'texto_limpio': limpiar_texto(texto_as400),
        'estado_normalizado': None,
        'metodo_usado': None,
        'confianza': 0.0,
        'explicacion': '',
        'requiere_revision': False,
        'categoria': 'SIN_MATCH'
    }
    
    # NIVEL 1: Detective Exacto
    estado, confianza, explicacion = detective_exacto(texto_as400, df_sepomex)
    if estado:
        resultado.update({
            'estado_normalizado': estado,
            'metodo_usado': 'EXACTO',
            'confianza': confianza,
            'explicacion': explicacion,
            'categoria': 'EXACTO'
        })
        return resultado
    
    # NIVEL 2: Detective Fuzzy Alto (80%+)
    estado, confianza, explicacion = detective_fuzzy(texto_as400, df_sepomex, 80)
    if estado:
        resultado.update({
            'estado_normalizado': estado,
            'metodo_usado': 'FUZZY_ALTO',
            'confianza': confianza,
            'explicacion': explicacion,
            'categoria': 'CONFIABLE'
        })
        return resultado
    
    # NIVEL 3: Detective Semántico
    estado, confianza, explicacion = detective_semantico(texto_as400, df_sepomex)
    if estado:
        resultado.update({
            'estado_normalizado': estado,
            'metodo_usado': 'SEMANTICO',
            'confianza': confianza,
            'explicacion': explicacion,
            'categoria': 'CONFIABLE'
        })
        return resultado
    
    # NIVEL 4: Detective Fuzzy Bajo (60%+)
    estado, confianza, explicacion = detective_fuzzy(texto_as400, df_sepomex, 60)
    if estado:
        resultado.update({
            'estado_normalizado': estado,
            'metodo_usado': 'FUZZY_BAJO',
            'confianza': confianza,
            'explicacion': explicacion,
            'categoria': 'REVISAR',
            'requiere_revision': True
        })
        return resultado
    
    # No se encontró nada
    resultado.update({
        'metodo_usado': 'NINGUNO',
        'explicacion': 'No se encontró coincidencia con ningún método',
        'categoria': 'SIN_MATCH',
        'requiere_revision': True
    })
    
    return resultado

# ========================================
# 7. PROCESADOR DE LOTES - MANEJA MUCHOS DATOS
# ========================================

def procesar_lote_estados(archivo_as400, archivo_sepomex):
    """
    💡 Esta función procesa muchos registros de una vez
    Es como tener una fábrica de detectives trabajando en paralelo
    
    ¿Qué hace?
    1. Lee los archivos CSV
    2. Aplica el detective principal a cada registro
    3. Calcula estadísticas del proceso
    4. Guarda los resultados
    """
    
    print(f"📖 Leyendo datos de AS400: {archivo_as400}")
    try:
        df_as400 = pd.read_csv(archivo_as400)
        print(f"   ✅ Leídos {len(df_as400)} registros de AS400")
    except Exception as e:
        print(f"   ❌ Error leyendo AS400: {e}")
        return None
    
    print(f"📖 Leyendo datos de SEPOMEX: {archivo_sepomex}")
    try:
        df_sepomex = pd.read_csv(archivo_sepomex)
        print(f"   ✅ Leídos {len(df_sepomex)} estados de SEPOMEX")
    except Exception as e:
        print(f"   ❌ Error leyendo SEPOMEX: {e}")
        return None
    
    print("🔍 Iniciando proceso de normalización...")
    
    resultados = []
    estadisticas = {
        'total': 0,
        'exactos': 0,
        'fuzzy_alto': 0,
        'fuzzy_bajo': 0,
        'semanticos': 0,
        'sin_match': 0,
        'requieren_revision': 0
    }
    
    # Procesar cada registro de AS400
    for idx, row in df_as400.iterrows():
        texto_estado = row.get('nombre_original', '')
        
        # Aplicar el detective principal
        resultado = detective_principal(texto_estado, df_sepomex)
        
        # Agregar información adicional del registro original
        resultado.update({
            'id_as400': idx,
            'division': row.get('division', ''),
            'esquema': row.get('esquema', ''),
            'clave_original': row.get('clave_original', ''),
            'fecha_proceso': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        resultados.append(resultado)
        
        # Actualizar estadísticas
        estadisticas['total'] += 1
        metodo = resultado['metodo_usado']
        
        if metodo == 'EXACTO':
            estadisticas['exactos'] += 1
        elif metodo == 'FUZZY_ALTO':
            estadisticas['fuzzy_alto'] += 1
        elif metodo == 'FUZZY_BAJO':
            estadisticas['fuzzy_bajo'] += 1
        elif metodo == 'SEMANTICO':
            estadisticas['semanticos'] += 1
        else:
            estadisticas['sin_match'] += 1
        
        if resultado['requiere_revision']:
            estadisticas['requieren_revision'] += 1
        
        # Mostrar progreso cada 10 registros
        if (idx + 1) % 10 == 0 or (idx + 1) == len(df_as400):
            print(f"   🔄 Procesados: {idx + 1}/{len(df_as400)}")
    
    # Crear DataFrame con resultados
    df_resultados = pd.DataFrame(resultados)
    
    return df_resultados, estadisticas

# ========================================
# 8. FUNCIÓN PRINCIPAL - EJECUTA TODO
# ========================================

def ejecutar_normalizacion():
    """
    💡 Esta es la función principal que ejecuta todo el proceso
    """
    
    print("🚀 INICIANDO NORMALIZACIÓN DE ESTADOS")
    print("=" * 50)
    
    # Rutas de archivos
    archivo_dds = "data/raw/DES/estados_dds.csv"
    archivo_db2 = "data/raw/DES/estados_db2.csv"
    archivo_sepomex = "data/reference/sepomex/estados_sepomex.csv"
    
    # Verificar que existan los archivos
    archivos = [archivo_dds, archivo_db2, archivo_sepomex]
    for archivo in archivos:
        if not os.path.exists(archivo):
            print(f"❌ No se encontró: {archivo}")
            print("💡 Ejecuta primero: python crear_datos_simple.py")
            return
    
    print("✅ Todos los archivos encontrados")
    
    # Procesar DDS
    print("\n🔍 PROCESANDO ESQUEMA DDS...")
    df_resultados_dds, stats_dds = procesar_lote_estados(archivo_dds, archivo_sepomex)
    
    # Procesar DB2
    print("\n🔍 PROCESANDO ESQUEMA DB2...")
    df_resultados_db2, stats_db2 = procesar_lote_estados(archivo_db2, archivo_sepomex)
    
    # Guardar resultados
    print("\n💾 GUARDANDO RESULTADOS...")
    
    os.makedirs("data/processed/DES", exist_ok=True)
    
    archivo_resultado_dds = "data/processed/DES/estados_normalizados_dds.csv"
    archivo_resultado_db2 = "data/processed/DES/estados_normalizados_db2.csv"
    
    df_resultados_dds.to_csv(archivo_resultado_dds, index=False, encoding='utf-8')
    df_resultados_db2.to_csv(archivo_resultado_db2, index=False, encoding='utf-8')
    
    print(f"✅ Resultados DDS guardados: {archivo_resultado_dds}")
    print(f"✅ Resultados DB2 guardados: {archivo_resultado_db2}")
    
    # Mostrar estadísticas
    mostrar_estadisticas("DDS", stats_dds)
    mostrar_estadisticas("DB2", stats_db2)
    
    # Mostrar ejemplos de resultados
    mostrar_ejemplos_resultados(df_resultados_dds, "DDS")
    
    print("\n🎉 ¡NORMALIZACIÓN COMPLETADA!")
    return df_resultados_dds, df_resultados_db2

def mostrar_estadisticas(esquema, stats):
    """Mostrar estadísticas del proceso"""
    
    print(f"\n📊 ESTADÍSTICAS {esquema}:")
    print("-" * 30)
    print(f"   Total procesados: {stats['total']}")
    print(f"   ✅ Exactos: {stats['exactos']}")
    print(f"   🎯 Fuzzy alto: {stats['fuzzy_alto']}")
    print(f"   🔍 Semánticos: {stats['semanticos']}")
    print(f"   ⚠️  Fuzzy bajo: {stats['fuzzy_bajo']}")
    print(f"   ❌ Sin match: {stats['sin_match']}")
    print(f"   📋 Requieren revisión: {stats['requieren_revision']}")
    
    if stats['total'] > 0:
        exitosos = stats['exactos'] + stats['fuzzy_alto'] + stats['semanticos']
        porcentaje = (exitosos / stats['total']) * 100
        print(f"   🎯 Éxito general: {porcentaje:.1f}%")

def mostrar_ejemplos_resultados(df_resultados, esquema):
    """Mostrar ejemplos de los resultados"""
    
    print(f"\n👀 EJEMPLOS DE RESULTADOS {esquema}:")
    print("-" * 40)
    
    # Mostrar algunos casos interesantes
    for _, row in df_resultados.head(5).iterrows():
        print(f"   '{row['texto_original']}' → '{row['estado_normalizado']}'")
        print(f"      Método: {row['metodo_usado']} | Confianza: {row['confianza']:.2f}")
        print(f"      {row['explicacion']}")
        print()

# ========================================
# 9. EJECUCIÓN PRINCIPAL
# ========================================

if __name__ == "__main__":
    ejecutar_normalizacion()