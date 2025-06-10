"""
Migración de Base de Datos para Sistema Asíncrono
================================================

Agrega las columnas necesarias sin afectar el sistema actual.
"""

try:
    from async_processor.utils import AsyncUtils
except ImportError:
    from utils import AsyncUtils

def migrate_database():
    """Agregar columnas necesarias para sistema asíncrono"""
    
    print("🔧 Iniciando migración de base de datos...")
    
    try:
        conn = AsyncUtils.get_db_connection()
        if not conn:
            print("❌ No se pudo conectar a la base de datos")
            return False
        
        cursor = conn.cursor()
        
        # Lista de columnas a agregar
        migrations = [
            {
                'column': 'processing_mode',
                'definition': 'VARCHAR(20) DEFAULT \'SINCRONO\'',
                'description': 'Modo de procesamiento (SINCRONO/ASINCRONO)'
            },
            {
                'column': 'task_id',
                'definition': 'VARCHAR(100)',
                'description': 'ID único de la tarea asíncrona'
            },
            {
                'column': 'estimated_duration',
                'definition': 'INTEGER DEFAULT 0',
                'description': 'Duración estimada en segundos'
            },
            {
                'column': 'worker_id',
                'definition': 'VARCHAR(50)',
                'description': 'ID del worker que procesa la tarea'
            }
        ]
        
        successful_migrations = 0
        
        for migration in migrations:
            try:
                print(f"  Agregando columna: {migration['column']}")
                
                # Verificar si la columna ya existe
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'archivos_cargados' 
                    AND column_name = %s
                """, (migration['column'],))
                
                if cursor.fetchone():
                    print(f"    ✅ {migration['column']} ya existe")
                else:
                    # Agregar la columna
                    sql = f"ALTER TABLE archivos_cargados ADD COLUMN IF NOT EXISTS {migration['column']} {migration['definition']}"
                    cursor.execute(sql)
                    print(f"    ✅ {migration['column']} agregada: {migration['description']}")
                
                successful_migrations += 1
                
            except Exception as e:
                print(f"    ❌ Error con {migration['column']}: {e}")
        
        # Hacer commit de todos los cambios
        conn.commit()
        
        print(f"\n✅ Migración completada: {successful_migrations}/{len(migrations)} columnas procesadas")
        
        # Verificar estructura final
        print("\n🔍 Verificando estructura final...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'archivos_cargados'
            AND column_name IN ('processing_mode', 'task_id', 'estimated_duration', 'worker_id')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        if columns:
            print("📋 Columnas agregadas:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']} (default: {col['column_default']})")
        else:
            print("⚠️ No se encontraron las columnas nuevas")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error general en migración: {e}")
        return False

def verify_migration():
    """Verificar que la migración funcionó"""
    
    print("\n🧪 Verificando migración...")
    
    try:
        conn = AsyncUtils.get_db_connection()
        cursor = conn.cursor()
        
        # Probar insertar un registro de prueba
        test_task_id = "test_migration_12345"
        
        cursor.execute("""
            INSERT INTO archivos_cargados 
            (id_archivo, nombre_archivo, tipo_catalogo, division, total_registros,
             usuario, estado_procesamiento, processing_mode, task_id, estimated_duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            test_task_id,
            "test_migration.csv",
            "ESTADOS",
            "TEST",
            100,
            "test_user",
            "PENDING",
            "ASINCRONO",
            test_task_id,
            30
        ))
        
        # Verificar que se insertó
        cursor.execute("SELECT * FROM archivos_cargados WHERE task_id = %s", (test_task_id,))
        result = cursor.fetchone()
        
        if result:
            print("✅ Prueba de inserción exitosa")
            print(f"  - processing_mode: {result['processing_mode']}")
            print(f"  - task_id: {result['task_id']}")
            print(f"  - estimated_duration: {result['estimated_duration']}")
            
            # Limpiar registro de prueba
            cursor.execute("DELETE FROM archivos_cargados WHERE task_id = %s", (test_task_id,))
            conn.commit()
            print("✅ Registro de prueba eliminado")
            
        else:
            print("❌ No se pudo insertar registro de prueba")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

if __name__ == "__main__":
    print("🚀 MIGRACIÓN DE BASE DE DATOS PARA SISTEMA ASÍNCRONO")
    print("=" * 60)
    
    # Ejecutar migración
    success = migrate_database()
    
    if success:
        # Verificar que funcionó
        verify_success = verify_migration()
        
        if verify_success:
            print("\n🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
            print("✅ El sistema asíncrono ya puede usar la base de datos")
        else:
            print("\n⚠️ Migración completada pero falló la verificación")
    else:
        print("\n❌ Error en la migración")
    
    print("\n📝 SIGUIENTE PASO: Ejecutar el test del queue_manager otra vez")