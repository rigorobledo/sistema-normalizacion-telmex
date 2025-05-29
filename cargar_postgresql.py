# ========================================
# ARCHIVO: cargar_postgresql.py
# CARGAR DATOS NORMALIZADOS A POSTGRESQL
# ========================================

"""
💡 ¿QUÉ HACE ESTE ARCHIVO?
Toma todos los archivos CSV normalizados y los carga en PostgreSQL
creando una base de datos completa y estructurada.

Estructura de tablas que se crearán:
- estados_normalizados
- municipios_normalizados  
- colonias_normalizadas
- metricas_procesamiento
- log_normalizacion
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import os
from datetime import datetime
import glob

# Configuración de base de datos (usar la misma de config.py)
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'normalizacion_domicilios',
    'user': 'postgres',
    'password': 'admin123'  # 🔑 Cambiar por tu contraseña
}

print("🗄️ INICIANDO CARGA A POSTGRESQL...")

# ========================================
# 1. CREAR ESTRUCTURA DE TABLAS
# ========================================

def crear_tablas_postgresql():
    """Crear las tablas necesarias en PostgreSQL"""
    
    print("📋 Creando estructura de tablas...")
    
    # SQL para crear tablas
    sql_tablas = """
    -- Tabla principal de estados normalizados
    CREATE TABLE IF NOT EXISTS estados_normalizados (
        id SERIAL PRIMARY KEY,
        division VARCHAR(10) NOT NULL,
        esquema VARCHAR(10) NOT NULL,
        clave_original VARCHAR(20),
        texto_original VARCHAR(200),
        texto_limpio VARCHAR(200),
        estado_normalizado VARCHAR(100),
        metodo_usado VARCHAR(50),
        confianza DECIMAL(5,4),
        categoria VARCHAR(50),
        requiere_revision BOOLEAN DEFAULT FALSE,
        explicacion TEXT,
        fecha_proceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Tabla de municipios normalizados
    CREATE TABLE IF NOT EXISTS municipios_normalizados (
        id SERIAL PRIMARY KEY,
        division VARCHAR(10) NOT NULL,
        esquema VARCHAR(10) NOT NULL,
        clave_original VARCHAR(20),
        texto_original VARCHAR(200),
        texto_limpio VARCHAR(200),
        municipio_normalizado VARCHAR(100),
        metodo_usado VARCHAR(50),
        confianza DECIMAL(5,4),
        categoria VARCHAR(50),
        requiere_revision BOOLEAN DEFAULT FALSE,
        explicacion TEXT,
        fecha_proceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Tabla de colonias normalizadas
    CREATE TABLE IF NOT EXISTS colonias_normalizadas (
        id SERIAL PRIMARY KEY,
        division VARCHAR(10) NOT NULL,
        esquema VARCHAR(10) NOT NULL,
        clave_original VARCHAR(20),
        codigo_postal VARCHAR(10),
        texto_original VARCHAR(200),
        texto_limpio VARCHAR(200),
        colonia_normalizada VARCHAR(150),
        metodo_usado VARCHAR(50),
        confianza DECIMAL(5,4),
        categoria VARCHAR(50),
        requiere_revision BOOLEAN DEFAULT FALSE,
        explicacion TEXT,
        fecha_proceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Tabla de métricas del proceso
    CREATE TABLE IF NOT EXISTS metricas_procesamiento (
        id SERIAL PRIMARY KEY,
        catalogo VARCHAR(50) NOT NULL,
        division VARCHAR(10) NOT NULL,
        esquema VARCHAR(10) NOT NULL,
        total_registros INTEGER,
        registros_exitosos INTEGER,
        porcentaje_exito DECIMAL(5,2),
        confianza_promedio DECIMAL(5,4),
        metodos_utilizados JSONB,
        requieren_revision INTEGER,
        tiempo_procesamiento_segundos DECIMAL(10,3),
        fecha_proceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Tabla de log de normalizaciones
    CREATE TABLE IF NOT EXISTS log_normalizacion (
        id SERIAL PRIMARY KEY,
        proceso VARCHAR(100) NOT NULL,
        estado VARCHAR(50) NOT NULL,
        mensaje TEXT,
        detalles JSONB,
        fecha_log TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Índices para mejor rendimiento
    CREATE INDEX IF NOT EXISTS idx_estados_division_esquema ON estados_normalizados(division, esquema);
    CREATE INDEX IF NOT EXISTS idx_estados_metodo ON estados_normalizados(metodo_usado);
    CREATE INDEX IF NOT EXISTS idx_estados_revision ON estados_normalizados(requiere_revision);
    
    CREATE INDEX IF NOT EXISTS idx_municipios_division_esquema ON municipios_normalizados(division, esquema);
    CREATE INDEX IF NOT EXISTS idx_municipios_metodo ON municipios_normalizados(metodo_usado);
    
    CREATE INDEX IF NOT EXISTS idx_colonias_division_esquema ON colonias_normalizadas(division, esquema);
    CREATE INDEX IF NOT EXISTS idx_colonias_codigo_postal ON colonias_normalizadas(codigo_postal);
    CREATE INDEX IF NOT EXISTS idx_colonias_metodo ON colonias_normalizadas(metodo_usado);
    """
    
    try:
        # Crear conexión
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        # Ejecutar SQL
        with engine.connect() as conn:
            conn.execute(text(sql_tablas))
            conn.commit()
        
        print("✅ Tablas creadas correctamente")
        
        # Log del proceso
        registrar_log("CREAR_TABLAS", "SUCCESS", "Estructura de tablas creada", {
            "tablas": ["estados_normalizados", "municipios_normalizados", "colonias_normalizadas", "metricas_procesamiento", "log_normalizacion"]
        })
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        registrar_log("CREAR_TABLAS", "ERROR", str(e), {})
        return False

# ========================================
# 2. CARGAR DATOS DE ESTADOS
# ========================================

def cargar_estados():
    """Cargar datos normalizados de estados"""
    
    print("\n🏛️ Cargando estados normalizados...")
    
    archivos_estados = [
        "data/processed/DES/estados_normalizados_dds.csv",
        "data/processed/DES/estados_normalizados_db2.csv"
    ]
    
    registros_cargados = 0
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        for archivo in archivos_estados:
            if os.path.exists(archivo):
                print(f"   📄 Procesando: {archivo}")
                
                # Leer CSV
                df = pd.read_csv(archivo)
                
                # Mapear columnas al esquema de PostgreSQL
                df_mapped = df.copy()
                
                # Renombrar columnas para que coincidan con la tabla
                column_mapping = {
                    'estado_normalizado': 'estado_normalizado',
                    'valor_normalizado': 'estado_normalizado',  # Por si usa el nombre nuevo
                }
                
                for old_col, new_col in column_mapping.items():
                    if old_col in df_mapped.columns:
                        df_mapped = df_mapped.rename(columns={old_col: new_col})
                
                # Agregar columnas faltantes si no existen
                columnas_requeridas = [
                    'division', 'esquema', 'clave_original', 'texto_original', 
                    'texto_limpio', 'estado_normalizado', 'metodo_usado', 
                    'confianza', 'categoria', 'requiere_revision', 'explicacion'
                ]
                
                for col in columnas_requeridas:
                    if col not in df_mapped.columns:
                        df_mapped[col] = None
                
                # Limpiar datos antes de insertar
                df_final = df_mapped[columnas_requeridas].copy()
                df_final = df_final.fillna('')
                
                # Convertir tipos de datos
                if 'confianza' in df_final.columns:
                    df_final['confianza'] = pd.to_numeric(df_final['confianza'], errors='coerce')
                
                if 'requiere_revision' in df_final.columns:
                    df_final['requiere_revision'] = df_final['requiere_revision'].astype(bool)
                
                # Insertar en PostgreSQL
                df_final.to_sql('estados_normalizados', engine, if_exists='append', index=False)
                
                registros_archivo = len(df_final)
                registros_cargados += registros_archivo
                print(f"      ✅ {registros_archivo} registros cargados")
                
            else:
                print(f"   ⚠️  No encontrado: {archivo}")
        
        print(f"✅ Total estados cargados: {registros_cargados}")
        
        registrar_log("CARGAR_ESTADOS", "SUCCESS", f"{registros_cargados} registros cargados", {
            "archivos_procesados": len([a for a in archivos_estados if os.path.exists(a)]),
            "registros_totales": registros_cargados
        })
        
        return registros_cargados
        
    except Exception as e:
        print(f"❌ Error cargando estados: {e}")
        registrar_log("CARGAR_ESTADOS", "ERROR", str(e), {})
        return 0

# ========================================
# 3. CARGAR DATOS DE MUNICIPIOS
# ========================================

def cargar_municipios():
    """Cargar datos normalizados de municipios"""
    
    print("\n🏢 Cargando municipios normalizados...")
    
    archivos_municipios = [
        "data/processed/DES/municipios/municipios_normalizados_dds.csv",
        "data/processed/DES/municipios/municipios_normalizados_db2.csv"
    ]
    
    registros_cargados = 0
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        for archivo in archivos_municipios:
            if os.path.exists(archivo):
                print(f"   📄 Procesando: {archivo}")
                
                df = pd.read_csv(archivo)
                
                # Mapear columnas
                column_mapping = {
                    'valor_normalizado': 'municipio_normalizado',
                    'municipio_normalizado': 'municipio_normalizado',
                }
                
                df_mapped = df.copy()
                for old_col, new_col in column_mapping.items():
                    if old_col in df_mapped.columns:
                        df_mapped = df_mapped.rename(columns={old_col: new_col})
                
                # Columnas para municipios
                columnas_requeridas = [
                    'division', 'esquema', 'clave_original', 'texto_original', 
                    'texto_limpio', 'municipio_normalizado', 'metodo_usado', 
                    'confianza', 'categoria', 'requiere_revision', 'explicacion'
                ]
                
                for col in columnas_requeridas:
                    if col not in df_mapped.columns:
                        df_mapped[col] = None
                
                df_final = df_mapped[columnas_requeridas].copy()
                df_final = df_final.fillna('')
                
                # Convertir tipos
                if 'confianza' in df_final.columns:
                    df_final['confianza'] = pd.to_numeric(df_final['confianza'], errors='coerce')
                
                if 'requiere_revision' in df_final.columns:
                    df_final['requiere_revision'] = df_final['requiere_revision'].astype(bool)
                
                # Insertar
                df_final.to_sql('municipios_normalizados', engine, if_exists='append', index=False)
                
                registros_archivo = len(df_final)
                registros_cargados += registros_archivo
                print(f"      ✅ {registros_archivo} registros cargados")
                
            else:
                print(f"   ⚠️  No encontrado: {archivo}")
        
        print(f"✅ Total municipios cargados: {registros_cargados}")
        
        registrar_log("CARGAR_MUNICIPIOS", "SUCCESS", f"{registros_cargados} registros cargados", {
            "registros_totales": registros_cargados
        })
        
        return registros_cargados
        
    except Exception as e:
        print(f"❌ Error cargando municipios: {e}")
        registrar_log("CARGAR_MUNICIPIOS", "ERROR", str(e), {})
        return 0

# ========================================
# 4. CARGAR DATOS DE COLONIAS
# ========================================

def cargar_colonias():
    """Cargar datos normalizados de colonias"""
    
    print("\n🏘️ Cargando colonias normalizadas...")
    
    archivos_colonias = [
        "data/processed/DES/colonias/colonias_normalizadas_dds.csv",
        "data/processed/DES/colonias/colonias_normalizadas_db2.csv",
        "data/processed/DES/colonias/colonias_masivo_normalizado.csv"
    ]
    
    registros_cargados = 0
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        for archivo in archivos_colonias:
            if os.path.exists(archivo):
                print(f"   📄 Procesando: {archivo}")
                
                df = pd.read_csv(archivo)
                
                # Mapear columnas
                column_mapping = {
                    'valor_normalizado': 'colonia_normalizada',
                    'colonia_normalizada': 'colonia_normalizada',
                }
                
                df_mapped = df.copy()
                for old_col, new_col in column_mapping.items():
                    if old_col in df_mapped.columns:
                        df_mapped = df_mapped.rename(columns={old_col: new_col})
                
                # Columnas para colonias
                columnas_requeridas = [
                    'division', 'esquema', 'clave_original', 'codigo_postal',
                    'texto_original', 'texto_limpio', 'colonia_normalizada', 
                    'metodo_usado', 'confianza', 'categoria', 'requiere_revision', 'explicacion'
                ]
                
                for col in columnas_requeridas:
                    if col not in df_mapped.columns:
                        df_mapped[col] = None
                
                df_final = df_mapped[columnas_requeridas].copy()
                df_final = df_final.fillna('')
                
                # Convertir tipos
                if 'confianza' in df_final.columns:
                    df_final['confianza'] = pd.to_numeric(df_final['confianza'], errors='coerce')
                
                if 'requiere_revision' in df_final.columns:
                    df_final['requiere_revision'] = df_final['requiere_revision'].astype(bool)
                
                # Insertar
                df_final.to_sql('colonias_normalizadas', engine, if_exists='append', index=False)
                
                registros_archivo = len(df_final)
                registros_cargados += registros_archivo
                print(f"      ✅ {registros_archivo} registros cargados")
                
            else:
                print(f"   ⚠️  No encontrado: {archivo}")
        
        print(f"✅ Total colonias cargadas: {registros_cargados}")
        
        registrar_log("CARGAR_COLONIAS", "SUCCESS", f"{registros_cargados} registros cargados", {
            "registros_totales": registros_cargados
        })
        
        return registros_cargados
        
    except Exception as e:
        print(f"❌ Error cargando colonias: {e}")
        registrar_log("CARGAR_COLONIAS", "ERROR", str(e), {})
        return 0

# ========================================
# 5. GENERAR MÉTRICAS Y ESTADÍSTICAS
# ========================================

def generar_metricas_db():
    """Generar métricas y estadísticas en la base de datos"""
    
    print("\n📊 Generando métricas en base de datos...")
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        # Métricas de estados
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    'estados' as catalogo,
                    division,
                    esquema,
                    COUNT(*) as total_registros,
                    COUNT(CASE WHEN estado_normalizado IS NOT NULL AND estado_normalizado != '' THEN 1 END) as registros_exitosos,
                    ROUND(
                        (COUNT(CASE WHEN estado_normalizado IS NOT NULL AND estado_normalizado != '' THEN 1 END) * 100.0 / COUNT(*)), 2
                    ) as porcentaje_exito,
                    ROUND(AVG(CASE WHEN confianza > 0 THEN confianza END), 4) as confianza_promedio,
                    COUNT(CASE WHEN requiere_revision = true THEN 1 END) as requieren_revision
                FROM estados_normalizados 
                GROUP BY division, esquema
            """))
            
            for row in result:
                # Insertar métricas
                conn.execute(text("""
                    INSERT INTO metricas_procesamiento 
                    (catalogo, division, esquema, total_registros, registros_exitosos, 
                     porcentaje_exito, confianza_promedio, requieren_revision)
                    VALUES (:catalogo, :division, :esquema, :total, :exitosos, 
                            :porcentaje, :confianza, :revision)
                """), {
                    'catalogo': row[0],
                    'division': row[1], 
                    'esquema': row[2],
                    'total': row[3],
                    'exitosos': row[4],
                    'porcentaje': row[5],
                    'confianza': row[6],
                    'revision': row[7]
                })
            
            conn.commit()
        
        print("✅ Métricas generadas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error generando métricas: {e}")
        return False

# ========================================
# 6. FUNCIONES DE UTILIDAD
# ========================================

def registrar_log(proceso, estado, mensaje, detalles):
    """Registrar eventos en el log de normalizacion"""
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO log_normalizacion (proceso, estado, mensaje, detalles)
                VALUES (:proceso, :estado, :mensaje, :detalles)
            """), {
                'proceso': proceso,
                'estado': estado,
                'mensaje': mensaje,
                'detalles': str(detalles) if detalles else '{}'
            })
            conn.commit()
            
    except Exception as e:
        print(f"⚠️  Error registrando log: {e}")

def verificar_conexion():
    """Verificar conexión a PostgreSQL"""
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conexión exitosa a PostgreSQL")
            print(f"   Versión: {version}")
            return True
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("\n🔧 POSIBLES SOLUCIONES:")
        print("1. Verifica que PostgreSQL esté corriendo")
        print("2. Revisa la contraseña en DATABASE_CONFIG")
        print("3. Confirma que la base de datos 'normalizacion_domicilios' existe")
        return False

def mostrar_resumen_final():
    """Mostrar resumen final de la carga"""
    
    print("\n" + "="*60)
    print("📋 RESUMEN FINAL DE CARGA A POSTGRESQL")
    print("="*60)
    
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        
        with engine.connect() as conn:
            # Contar registros por tabla
            tablas = ['estados_normalizados', 'municipios_normalizados', 'colonias_normalizadas']
            
            for tabla in tablas:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    count = result.fetchone()[0]
                    print(f"📊 {tabla}: {count:,} registros")
                except:
                    print(f"⚠️  {tabla}: No disponible")
            
            # Métricas generales
            result = conn.execute(text("""
                SELECT COUNT(*) FROM metricas_procesamiento
            """))
            metricas_count = result.fetchone()[0]
            print(f"📈 Métricas generadas: {metricas_count}")
            
            # Log de procesos
            result = conn.execute(text("""
                SELECT COUNT(*) FROM log_normalizacion
            """))
            log_count = result.fetchone()[0]
            print(f"📝 Eventos registrados: {log_count}")
        
        print("\n🎉 ¡CARGA COMPLETADA EXITOSAMENTE!")
        print("🌐 Datos disponibles en PostgreSQL para consultas y análisis")
        
    except Exception as e:
        print(f"❌ Error mostrando resumen: {e}")

# ========================================
# 7. FUNCIÓN PRINCIPAL
# ========================================

def main():
    """Función principal de carga a PostgreSQL"""
    
    print("🚀 INICIANDO CARGA DE DATOS NORMALIZADOS A POSTGRESQL")
    print("=" * 60)
    
    # Verificar conexión
    if not verificar_conexion():
        return False
    
    # Crear estructura de tablas
    if not crear_tablas_postgresql():
        return False
    
    # Cargar datos por catálogo
    estados_cargados = cargar_estados()
    municipios_cargados = cargar_municipios()
    colonias_cargadas = cargar_colonias()
    
    # Generar métricas
    generar_metricas_db()
    
    # Mostrar resumen
    mostrar_resumen_final()
    
    # Log final
    registrar_log("CARGA_COMPLETA", "SUCCESS", "Proceso completado", {
        "estados": estados_cargados,
        "municipios": municipios_cargados,
        "colonias": colonias_cargadas,
        "fecha_fin": datetime.now().isoformat()
    })
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print("1. Conéctate a PostgreSQL para ver los datos")
    print("2. Ejecuta consultas SQL para análisis")
    print("3. Usa los datos normalizados en tus aplicaciones")
    
    return True

if __name__ == "__main__":
    main()