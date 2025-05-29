# ========================================
# LIMPIEZA COMPLETA DE BASE DE DATOS
# RESET TOTAL DEL SISTEMA
# ========================================

"""
Script para limpiar completamente la base de datos del sistema de normalización
Elimina todos los datos de prueba y deja el sistema como recién instalado

CUIDADO: Este script elimina TODOS los datos
"""

import pandas as pd
from sqlalchemy import text, create_engine
from datetime import datetime
import sys

# Configuración de la base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'normalizacion_domicilios',
    'user': 'postgres',
    'password': 'admin123'
}

def crear_conexion():
    """Crear conexión a PostgreSQL"""
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        return engine
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def mostrar_estado_actual():
    """Mostrar el estado actual de la base de datos"""
    
    print("📊 ESTADO ACTUAL DE LA BASE DE DATOS")
    print("=" * 50)
    
    engine = crear_conexion()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Contar registros en cada tabla
            tablas_sistema = [
                'referencias_normalizacion',
                'archivos_cargados', 
                'resultados_normalizacion'
            ]
            
            total_registros = 0
            
            for tabla in tablas_sistema:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    count = result.fetchone()[0]
                    total_registros += count
                    
                    if count > 0:
                        print(f"📋 {tabla}: {count:,} registros")
                    else:
                        print(f"📋 {tabla}: vacía")
                        
                except Exception as e:
                    print(f"⚠️ {tabla}: Error consultando ({str(e)[:50]}...)")
            
            print(f"\n📊 TOTAL REGISTROS: {total_registros:,}")
            
            # Mostrar información adicional si hay datos
            if total_registros > 0:
                print("\n🔍 DETALLES:")
                
                # Referencias por tipo
                try:
                    result = conn.execute(text("""
                        SELECT tipo_catalogo, COUNT(*) as total
                        FROM referencias_normalizacion
                        GROUP BY tipo_catalogo
                        ORDER BY tipo_catalogo
                    """))
                    
                    print("   📚 Referencias:")
                    for row in result:
                        print(f"      {row[0]}: {row[1]} referencias")
                        
                except:
                    pass
                
                # Archivos procesados
                try:
                    result = conn.execute(text("""
                        SELECT COUNT(DISTINCT nombre_archivo) as archivos,
                               SUM(total_registros) as registros_procesados
                        FROM archivos_cargados
                    """))
                    
                    row = result.fetchone()
                    if row and row[0]:
                        print(f"   📁 Archivos procesados: {row[0]}")
                        print(f"   📊 Registros procesados: {row[1]:,}")
                        
                except:
                    pass
            
            return True
            
    except Exception as e:
        print(f"❌ Error consultando estado: {e}")
        return False

def confirmar_limpieza():
    """Pedir confirmación antes de limpiar"""
    
    print("\n⚠️ CONFIRMACIÓN DE LIMPIEZA")
    print("=" * 30)
    print("Esta operación:")
    print("• 🗑️ Eliminará TODOS los datos de prueba")
    print("• 🗑️ Borrará todas las referencias cargadas")
    print("• 🗑️ Eliminará todos los archivos procesados")
    print("• 🗑️ Borrará todos los resultados de normalización")
    print("• ⚠️ NO se puede deshacer")
    
    print("\n¿Estás seguro de continuar?")
    print("Escribe 'CONFIRMAR' para proceder:")
    
    confirmacion = input().strip().upper()
    
    if confirmacion == 'CONFIRMAR':
        return True
    else:
        print("❌ Operación cancelada")
        return False

def limpiar_datos_completo():
    """Limpiar completamente todos los datos"""
    
    print("\n🧹 INICIANDO LIMPIEZA COMPLETA")
    print("=" * 40)
    
    engine = crear_conexion()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Orden de limpieza (por dependencias)
            operaciones_limpieza = [
                {
                    'tabla': 'resultados_normalizacion',
                    'descripcion': 'Resultados de normalización',
                    'sql': 'DELETE FROM resultados_normalizacion'
                },
                {
                    'tabla': 'archivos_cargados',
                    'descripcion': 'Archivos procesados',
                    'sql': 'DELETE FROM archivos_cargados'
                },
                {
                    'tabla': 'referencias_normalizacion',
                    'descripcion': 'Referencias (SEPOMEX/INEGI)',
                    'sql': 'DELETE FROM referencias_normalizacion'
                }
            ]
            
            registros_eliminados = 0
            
            for operacion in operaciones_limpieza:
                print(f"🗑️ Limpiando: {operacion['descripcion']}...")
                
                try:
                    # Contar antes de eliminar
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {operacion['tabla']}"))
                    count_antes = result.fetchone()[0]
                    
                    if count_antes > 0:
                        # Eliminar datos
                        result = conn.execute(text(operacion['sql']))
                        eliminados = result.rowcount
                        registros_eliminados += eliminados
                        
                        print(f"   ✅ Eliminados: {eliminados:,} registros")
                    else:
                        print(f"   ➡️ Ya estaba vacía")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    return False
            
            # Commit de todas las operaciones
            conn.commit()
            
            print(f"\n🎉 LIMPIEZA COMPLETADA")
            print(f"📊 Total eliminados: {registros_eliminados:,} registros")
            
            return True
            
    except Exception as e:
        print(f"❌ Error en limpieza: {e}")
        return False

def resetear_secuencias():
    """Resetear secuencias de auto-incremento (si las hay)"""
    
    print("\n🔄 RESETEANDO SECUENCIAS...")
    
    engine = crear_conexion()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Resetear secuencias de PostgreSQL (si existen)
            result = conn.execute(text("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
            """))
            
            secuencias = [row[0] for row in result]
            
            if secuencias:
                for secuencia in secuencias:
                    conn.execute(text(f"ALTER SEQUENCE {secuencia} RESTART WITH 1"))
                    print(f"   🔄 Reseteada: {secuencia}")
                
                conn.commit()
                print(f"✅ {len(secuencias)} secuencias reseteadas")
            else:
                print("➡️ No hay secuencias que resetear")
            
            return True
            
    except Exception as e:
        print(f"⚠️ Advertencia reseteando secuencias: {e}")
        return True  # No es crítico

def optimizar_base_datos():
    """Optimizar la base de datos después de la limpieza"""
    
    print("\n⚡ OPTIMIZANDO BASE DE DATOS...")
    
    engine = crear_conexion()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # VACUUM ANALYZE para recuperar espacio y actualizar estadísticas
            tablas = ['referencias_normalizacion', 'archivos_cargados', 'resultados_normalizacion']
            
            for tabla in tablas:
                print(f"   ⚡ Optimizando: {tabla}")
                conn.execute(text(f"VACUUM ANALYZE {tabla}"))
            
            conn.commit()
            print("✅ Optimización completada")
            
            return True
            
    except Exception as e:
        print(f"⚠️ Advertencia en optimización: {e}")
        return True  # No es crítico

def verificar_limpieza():
    """Verificar que la limpieza fue exitosa"""
    
    print("\n✅ VERIFICANDO LIMPIEZA...")
    
    engine = crear_conexion()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            tablas = ['referencias_normalizacion', 'archivos_cargados', 'resultados_normalizacion']
            
            todas_vacias = True
            
            for tabla in tablas:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                count = result.fetchone()[0]
                
                if count == 0:
                    print(f"   ✅ {tabla}: vacía")
                else:
                    print(f"   ❌ {tabla}: {count} registros restantes")
                    todas_vacias = False
            
            if todas_vacias:
                print("\n🎉 VERIFICACIÓN EXITOSA: Base de datos completamente limpia")
                return True
            else:
                print("\n⚠️ ADVERTENCIA: Algunos datos no se eliminaron completamente")
                return False
                
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def mostrar_instrucciones_post_limpieza():
    """Mostrar qué hacer después de la limpieza"""
    
    print("\n📋 INSTRUCCIONES POST-LIMPIEZA")
    print("=" * 40)
    print("""
🎯 ESTADO ACTUAL:
• Base de datos completamente limpia
• Sistema listo para uso en producción
• Todas las tablas vacías pero funcionales

🚀 PRÓXIMOS PASOS:

1️⃣ CARGAR REFERENCIAS REALES:
   • Obtener datos oficiales SEPOMEX/INEGI
   • Cargar usando: cargar_referencias_simple.py
   • O usar la interfaz de Streamlit

2️⃣ PROCESAR ARCHIVOS REALES:
   • Cargar archivos AS400 reales (no de prueba)
   • Usar el sistema normalmente en Streamlit

3️⃣ CONFIGURAR BACKUP:
   • Hacer backup antes de cargar datos reales
   • Comando: pg_dump -h localhost -U postgres normalizacion_domicilios > backup.sql

⚠️ RECORDATORIO:
• Las referencias de prueba fueron eliminadas
• Necesitas cargar referencias reales para que funcione la normalización
• El sistema está listo para producción
    """)

def main():
    """Función principal de limpieza"""
    
    print("🧹 SISTEMA DE LIMPIEZA COMPLETA")
    print("RESET TOTAL DE BASE DE DATOS")
    print("=" * 60)
    
    # Mostrar estado actual
    if not mostrar_estado_actual():
        print("❌ Error consultando estado actual")
        return
    
    # Pedir confirmación
    if not confirmar_limpieza():
        return
    
    print("\n🚀 INICIANDO PROCESO DE LIMPIEZA...")
    
    # Ejecutar limpieza
    if limpiar_datos_completo():
        
        # Resetear secuencias
        resetear_secuencias()
        
        # Optimizar BD
        optimizar_base_datos()
        
        # Verificar limpieza
        if verificar_limpieza():
            mostrar_instrucciones_post_limpieza()
            
            print("\n" + "=" * 60)
            print("🎉 LIMPIEZA COMPLETADA EXITOSAMENTE")
            print("✅ Sistema listo para producción")
        else:
            print("\n⚠️ Limpieza completada con advertencias")
    else:
        print("\n❌ Error en el proceso de limpieza")

# ========================================
# FUNCIONES ADICIONALES DE UTILIDAD
# ========================================

def limpieza_selectiva():
    """Opción para limpiar solo algunos tipos de datos"""
    
    print("\n🎯 LIMPIEZA SELECTIVA")
    print("=" * 30)
    
    opciones = {
        '1': ('Solo referencias', 'DELETE FROM referencias_normalizacion'),
        '2': ('Solo archivos procesados', 'DELETE FROM archivos_cargados; DELETE FROM resultados_normalizacion'),
        '3': ('Solo resultados', 'DELETE FROM resultados_normalizacion'),
        '4': ('Todo (limpieza completa)', 'COMPLETA')
    }
    
    print("Opciones de limpieza:")
    for key, (desc, _) in opciones.items():
        print(f"  {key}. {desc}")
    
    eleccion = input("\nElige una opción (1-4): ").strip()
    
    if eleccion in opciones:
        desc, sql = opciones[eleccion]
        
        if sql == 'COMPLETA':
            main()  # Limpieza completa
        else:
            print(f"\n🗑️ Ejecutando: {desc}")
            
            engine = crear_conexion()
            if engine:
                try:
                    with engine.connect() as conn:
                        # Ejecutar SQL de limpieza selectiva
                        for statement in sql.split(';'):
                            if statement.strip():
                                result = conn.execute(text(statement.strip()))
                                print(f"   ✅ Eliminados: {result.rowcount} registros")
                        
                        conn.commit()
                        print("✅ Limpieza selectiva completada")
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    # Verificar si se quiere limpieza selectiva
    if len(sys.argv) > 1 and sys.argv[1] == '--selectiva':
        limpieza_selectiva()
    else:
        main()