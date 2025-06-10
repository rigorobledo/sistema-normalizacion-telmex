# ========================================
# SCRIPT: reset_usuarios.py
# PROPÓSITO: Limpiar usuarios bloqueados y crear nuevo superusuario
# AUTOR: Sistema de Normalización Telmex
# ========================================

import os
import sys
import psycopg2
import hashlib
import secrets
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

# Cargar variables de entorno
try:
    load_dotenv()
except:
    pass

# ========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS
# ========================================

# DETECCIÓN AUTOMÁTICA DE AMBIENTE
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
IS_LOCAL = not IS_RAILWAY

def get_database_config():
    """Configuración de BD que funciona en ambos ambientes"""
    
    if IS_RAILWAY:
        # CONFIGURACIÓN PARA RAILWAY
        if 'DATABASE_URL' in os.environ:
            database_url = os.environ['DATABASE_URL']
            parsed = urlparse(database_url)
            
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:],
                'user': parsed.username,
                'password': parsed.password
            }
        else:
            # Variables manuales en Railway
            return {
                'host': os.environ['DB_HOST'],
                'port': int(os.environ.get('DB_PORT', 5432)),
                'database': os.environ['DB_NAME'],
                'user': os.environ['DB_USER'],
                'password': os.environ['DB_PASSWORD']
            }
    else:
        # CONFIGURACIÓN LOCAL
        return {
            'host': os.getenv('LOCAL_DB_HOST', 'localhost'),
            'port': int(os.getenv('LOCAL_DB_PORT', 5432)),
            'database': os.getenv('LOCAL_DB_NAME', 'normalizacion_domicilios'),
            'user': os.getenv('LOCAL_DB_USER', 'postgres'),
            'password': os.getenv('LOCAL_DB_PASSWORD', 'admin123')
        }

# ========================================
# 2. FUNCIONES DE GESTIÓN DE USUARIOS
# ========================================

def generar_hash_password(password):
    """Generar hash seguro de contraseña"""
    salt = secrets.token_hex(32)
    password_hash = hashlib.pbkdf2_hmac('sha256', 
                                       password.encode('utf-8'), 
                                       salt.encode('utf-8'), 
                                       100000)
    return password_hash.hex(), salt

def conectar_bd():
    """Conectar a la base de datos"""
    try:
        config = get_database_config()
        
        print(f"🔌 Conectando a {'Railway' if IS_RAILWAY else 'Local'}: {config['host']}:{config['port']}")
        print(f"📊 Base de datos: {config['database']}")
        
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        conn.autocommit = True
        print("✅ Conexión exitosa")
        return conn
        
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return None

def verificar_tabla_usuarios(cursor):
    """Verificar si existe la tabla usuarios"""
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'usuarios'
            )
        """)
        
        existe = cursor.fetchone()[0]
        
        if not existe:
            print("⚠️ Tabla 'usuarios' no existe. Creándola...")
            crear_tabla_usuarios(cursor)
        else:
            print("✅ Tabla 'usuarios' encontrada")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tabla: {e}")
        return False

def crear_tabla_usuarios(cursor):
    """Crear tabla de usuarios si no existe"""
    try:
        sql_usuarios = """
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            salt VARCHAR(255) NOT NULL,
            nombre_completo VARCHAR(100) NOT NULL,
            rol VARCHAR(20) NOT NULL DEFAULT 'USUARIO',
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_ultimo_acceso TIMESTAMP,
            creado_por UUID,
            intentos_fallidos INTEGER DEFAULT 0,
            bloqueado_hasta TIMESTAMP,
            
            CONSTRAINT chk_rol CHECK (rol IN ('SUPERUSUARIO', 'GERENTE', 'USUARIO')),
            CONSTRAINT chk_username_length CHECK (length(username) >= 3),
            CONSTRAINT chk_password_complexity CHECK (length(password_hash) > 0)
        );
        
        -- Índices para optimización
        CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);
        CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
        CREATE INDEX IF NOT EXISTS idx_usuarios_activo ON usuarios(activo);
        
        -- Tabla de sesiones activas
        CREATE TABLE IF NOT EXISTS sesiones_usuario (
            id_sesion UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_usuario UUID REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
            token_sesion VARCHAR(255) UNIQUE NOT NULL,
            ip_address INET,
            user_agent TEXT,
            fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_expiracion TIMESTAMP NOT NULL,
            activa BOOLEAN DEFAULT TRUE
        );
        
        CREATE INDEX IF NOT EXISTS idx_sesiones_token ON sesiones_usuario(token_sesion);
        CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones_usuario(id_usuario);
        """
        
        cursor.execute(sql_usuarios)
        print("✅ Tabla de usuarios creada correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tabla: {e}")
        return False

def listar_usuarios_actuales(cursor):
    """Listar usuarios actuales en el sistema"""
    try:
        cursor.execute("""
            SELECT username, email, nombre_completo, rol, activo, 
                   intentos_fallidos, bloqueado_hasta, fecha_creacion
            FROM usuarios 
            ORDER BY fecha_creacion DESC
        """)
        
        usuarios = cursor.fetchall()
        
        if usuarios:
            print(f"\n📋 USUARIOS ACTUALES ({len(usuarios)}):")
            print("=" * 80)
            
            for i, user in enumerate(usuarios, 1):
                username, email, nombre, rol, activo, intentos, bloqueado, fecha = user
                
                # Estado del usuario
                if bloqueado and bloqueado > datetime.now():
                    estado = f"🔒 BLOQUEADO hasta {bloqueado}"
                elif not activo:
                    estado = "❌ INACTIVO"
                elif intentos >= 5:
                    estado = f"⚠️ {intentos} intentos fallidos"
                else:
                    estado = "✅ ACTIVO"
                
                print(f"{i:2d}. {username:15} | {rol:12} | {estado}")
                print(f"    📧 {email}")
                print(f"    👤 {nombre}")
                print(f"    📅 Creado: {fecha}")
                print("-" * 80)
        else:
            print("📝 No hay usuarios en el sistema")
        
        return len(usuarios)
        
    except Exception as e:
        print(f"❌ Error listando usuarios: {e}")
        return 0

def verificar_tablas_dependientes(cursor):
    """Verificar qué tablas tienen claves foráneas hacia usuarios"""
    try:
        cursor.execute("""
            SELECT 
                tc.table_name, 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND ccu.table_name = 'usuarios'
            ORDER BY tc.table_name;
        """)
        
        dependencias = cursor.fetchall()
        
        if dependencias:
            print(f"\n🔍 TABLAS CON DEPENDENCIAS HACIA USUARIOS ({len(dependencias)}):")
            print("-" * 60)
            for tabla, columna, tabla_ref, columna_ref in dependencias:
                print(f"📋 {tabla}.{columna} → {tabla_ref}.{columna_ref}")
            print("-" * 60)
        
        return [dep[0] for dep in dependencias]  # Lista de nombres de tablas
        
    except Exception as e:
        print(f"⚠️ Error verificando dependencias: {e}")
        return []

def contar_registros_dependientes(cursor, tablas_dependientes):
    """Contar registros en tablas dependientes"""
    registros_por_tabla = {}
    
    for tabla in tablas_dependientes:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor.fetchone()[0]
            registros_por_tabla[tabla] = count
            
            if count > 0:
                print(f"📊 {tabla}: {count:,} registros")
        
        except Exception as e:
            print(f"⚠️ Error contando {tabla}: {e}")
            registros_por_tabla[tabla] = -1
    
    return registros_por_tabla

def eliminar_todos_usuarios(cursor):
    """Eliminar todos los usuarios del sistema manejando dependencias"""
    try:
        # 1. Contar usuarios antes
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_antes = cursor.fetchone()[0]
        
        if total_antes == 0:
            print("ℹ️ No hay usuarios para eliminar")
            return True
        
        print(f"\n🗑️ ELIMINANDO {total_antes} USUARIOS Y DEPENDENCIAS...")
        
        # 2. Verificar tablas dependientes
        tablas_dependientes = verificar_tablas_dependientes(cursor)
        
        if tablas_dependientes:
            print(f"\n📊 CONTANDO REGISTROS EN TABLAS DEPENDIENTES:")
            registros = contar_registros_dependientes(cursor, tablas_dependientes)
            
            total_dependientes = sum(count for count in registros.values() if count > 0)
            if total_dependientes > 0:
                print(f"\n⚠️ TOTAL REGISTROS DEPENDIENTES: {total_dependientes:,}")
        
        # 3. Eliminar en orden correcto (dependientes primero)
        eliminaciones_exitosas = 0
        
        # Lista completa de tablas a limpiar (en orden de dependencia)
        tablas_a_limpiar = [
            'auditoria_accesos',      # Nueva tabla detectada
            'sesiones_usuario',       # Tabla existente
            'resultados_normalizacion', # Puede tener creado_por
            'archivos_cargados',      # Puede tener usuario
            'configuracion_sistema'   # Puede tener modificado_por
        ]
        
        # Agregar tablas dependientes detectadas dinámicamente
        for tabla in tablas_dependientes:
            if tabla not in tablas_a_limpiar:
                tablas_a_limpiar.insert(0, tabla)  # Insertar al inicio por seguridad
        
        # Eliminar registros de tablas dependientes
        for tabla in tablas_a_limpiar:
            try:
                # Verificar si la tabla existe
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, (tabla,))
                
                if cursor.fetchone()[0]:
                    # Verificar si tiene columna que referencia usuarios
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        AND (column_name LIKE '%%usuario%%' OR column_name LIKE '%%creado_por%%' OR column_name LIKE '%%modificado_por%%')
                    """, (tabla,))
                    
                    columnas_usuario = cursor.fetchall()
                    
                    if columnas_usuario:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                        count_antes = cursor.fetchone()[0]
                        
                        if count_antes > 0:
                            cursor.execute(f"DELETE FROM {tabla}")
                            eliminados = cursor.rowcount
                            print(f"   🗑️ {tabla}: {eliminados:,} registros eliminados")
                            eliminaciones_exitosas += 1
                        else:
                            print(f"   ✅ {tabla}: ya está vacía")
                    else:
                        print(f"   ⚪ {tabla}: no tiene referencias a usuarios")
                else:
                    print(f"   ⚪ {tabla}: no existe")
                    
            except Exception as e:
                print(f"   ⚠️ Error limpiando {tabla}: {e}")
        
        # 4. Finalmente eliminar usuarios
        print(f"\n🗑️ ELIMINANDO USUARIOS...")
        cursor.execute("DELETE FROM usuarios")
        usuarios_eliminados = cursor.rowcount
        print(f"   🗑️ Usuarios eliminados: {usuarios_eliminados}")
        
        # 5. Verificar eliminación completa
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_despues = cursor.fetchone()[0]
        
        if total_despues == 0:
            print(f"\n✅ ELIMINACIÓN COMPLETA:")
            print(f"   ✅ {eliminaciones_exitosas} tablas dependientes limpiadas")
            print(f"   ✅ {usuarios_eliminados} usuarios eliminados")
            print(f"   ✅ Sistema listo para nuevo superusuario")
            return True
        else:
            print(f"⚠️ Quedan {total_despues} usuarios sin eliminar")
            return False
            
    except Exception as e:
        print(f"❌ Error eliminando usuarios: {e}")
        print("💡 Detalles del error:")
        print(f"   {str(e)}")
        return False

def crear_superusuario(cursor, username, email, password, nombre_completo):
    """Crear nuevo superusuario"""
    try:
        # Generar hash de contraseña
        password_hash, salt = generar_hash_password(password)
        
        cursor.execute("""
            INSERT INTO usuarios (
                username, email, password_hash, salt, nombre_completo, 
                rol, activo, fecha_creacion, intentos_fallidos
            )
            VALUES (%s, %s, %s, %s, %s, 'SUPERUSUARIO', TRUE, CURRENT_TIMESTAMP, 0)
            RETURNING id_usuario, username
        """, (username, email, password_hash, salt, nombre_completo))
        
        result = cursor.fetchone()
        user_id, created_username = result
        
        print(f"✅ Superusuario creado exitosamente:")
        print(f"   🆔 ID: {user_id}")
        print(f"   👤 Usuario: {created_username}")
        print(f"   📧 Email: {email}")
        print(f"   🎭 Rol: SUPERUSUARIO")
        print(f"   📅 Fecha: {datetime.now()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando superusuario: {e}")
        return False

# ========================================
# 3. SCRIPT PRINCIPAL
# ========================================

def eliminar_usuarios_modo_seguro(cursor):
    """Modo seguro: desactivar constraints temporalmente"""
    try:
        print("🛡️ INICIANDO MODO SEGURO (desactivar constraints)")
        
        # 1. Contar usuarios
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = cursor.fetchone()[0]
        
        if total_usuarios == 0:
            print("ℹ️ No hay usuarios para eliminar")
            return True
        
        print(f"🗑️ Eliminando {total_usuarios} usuarios en modo seguro...")
        
        # 2. Deshabilitar constraints temporalmente
        print("   🔧 Deshabilitando constraints de claves foráneas...")
        cursor.execute("SET session_replication_role = replica;")
        
        # 3. Obtener todas las tablas que pueden tener referencias
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name != 'usuarios'
            ORDER BY table_name
        """)
        
        todas_las_tablas = [row[0] for row in cursor.fetchall()]
        
        # 4. Limpiar tablas que pueden tener referencias a usuarios
        tablas_limpiadas = 0
        for tabla in todas_las_tablas:
            try:
                # Verificar si tiene columnas que referencian usuarios
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND (
                        column_name LIKE '%%usuario%%' 
                        OR column_name LIKE '%%creado_por%%' 
                        OR column_name LIKE '%%modificado_por%%'
                        OR column_name = 'id_usuario'
                        OR column_name = 'user_id'
                    )
                """, (tabla,))
                
                columnas = cursor.fetchall()
                
                if columnas:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute(f"DELETE FROM {tabla}")
                        eliminados = cursor.rowcount
                        print(f"   🗑️ {tabla}: {eliminados:,} registros")
                        tablas_limpiadas += 1
                
            except Exception as e:
                print(f"   ⚠️ Error en {tabla}: {e}")
        
        # 5. Eliminar usuarios
        cursor.execute("DELETE FROM usuarios")
        usuarios_eliminados = cursor.rowcount
        
        # 6. Reactivar constraints
        print("   🔧 Reactivando constraints...")
        cursor.execute("SET session_replication_role = DEFAULT;")
        
        # 7. Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        verificacion = cursor.fetchone()[0]
        
        if verificacion == 0:
            print(f"✅ MODO SEGURO COMPLETADO:")
            print(f"   ✅ {tablas_limpiadas} tablas limpiadas")
            print(f"   ✅ {usuarios_eliminados} usuarios eliminados")
            print(f"   ✅ Constraints reactivados")
            return True
        else:
            print(f"❌ Error: quedan {verificacion} usuarios")
            return False
            
    except Exception as e:
        # Asegurar que los constraints se reactiven
        try:
            cursor.execute("SET session_replication_role = DEFAULT;")
        except:
            pass
        
        print(f"❌ Error en modo seguro: {e}")
        return False

def main():
    """Función principal del script"""
    
    print("=" * 60)
    print("🔧 SCRIPT DE RESET DE USUARIOS")
    print("🏠 Sistema de Normalización Telmex")
    print("=" * 60)
    
    # 1. Conectar a la base de datos
    print("\n1️⃣ CONECTANDO A LA BASE DE DATOS")
    conn = conectar_bd()
    
    if not conn:
        print("❌ No se pudo conectar. Verifica la configuración.")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    # 2. Verificar tabla de usuarios
    print("\n2️⃣ VERIFICANDO TABLA DE USUARIOS")
    if not verificar_tabla_usuarios(cursor):
        print("❌ No se pudo verificar/crear la tabla")
        conn.close()
        sys.exit(1)
    
    # 3. Mostrar usuarios actuales
    print("\n3️⃣ USUARIOS ACTUALES")
    total_usuarios = listar_usuarios_actuales(cursor)
    
    # 4. Confirmación para eliminar
    if total_usuarios > 0:
        print(f"\n⚠️ ADVERTENCIA: Se eliminarán {total_usuarios} usuarios permanentemente")
        print("MÉTODOS DISPONIBLES:")
        print("1. Eliminación normal (recomendado)")
        print("2. Modo seguro (si hay muchas dependencias)")
        
        metodo = input("Selecciona método (1 o 2): ").strip()
        
        respuesta = input("¿Continuar? (escribir 'SI' para confirmar): ")
        
        if respuesta.upper() != 'SI':
            print("❌ Operación cancelada por el usuario")
            conn.close()
            sys.exit(0)
        
        # 5. Eliminar usuarios existentes
        print("\n4️⃣ ELIMINANDO USUARIOS EXISTENTES")
        
        if metodo == "2":
            exito = eliminar_usuarios_modo_seguro(cursor)
        else:
            exito = eliminar_todos_usuarios(cursor)
        
        if not exito:
            print("❌ Error eliminando usuarios")
            print("\n💡 SOLUCIONES:")
            print("1. Intenta con el 'Modo seguro' (opción 2)")
            print("2. Elimina manualmente la tabla 'auditoria_accesos'")
            print("3. Contacta al administrador de base de datos")
            conn.close()
            sys.exit(1)
    else:
        print("✅ No hay usuarios existentes")
    
    # 6. Crear nuevo superusuario
    print("\n5️⃣ CREANDO NUEVO SUPERUSUARIO")
    
    # Solicitar datos del nuevo usuario
    print("\n📝 Ingresa los datos del nuevo superusuario:")
    
    username = input("👤 Usuario (por defecto 'admin'): ").strip() or 'admin'
    email = input("📧 Email (por defecto 'admin@telmex.com'): ").strip() or 'admin@telmex.com'
    nombre = input("🏷️ Nombre completo (por defecto 'Administrador Sistema'): ").strip() or 'Administrador Sistema'
    
    # Contraseña con confirmación
    while True:
        password1 = input("🔒 Contraseña: ").strip()
        if len(password1) < 6:
            print("⚠️ La contraseña debe tener al menos 6 caracteres")
            continue
        
        password2 = input("🔒 Confirmar contraseña: ").strip()
        if password1 != password2:
            print("⚠️ Las contraseñas no coinciden")
            continue
        
        break
    
    # Crear superusuario
    if crear_superusuario(cursor, username, email, password1, nombre):
        print("\n🎉 PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        print("✅ Usuarios anteriores eliminados")
        print("✅ Dependencias limpiadas")
        print("✅ Nuevo superusuario creado")
        print(f"✅ Credenciales: {username} / {password1}")
        print("=" * 60)
        print("\n💡 Ahora puedes acceder al sistema con las nuevas credenciales")
    else:
        print("❌ Error creando el nuevo superusuario")
    
    # Cerrar conexión
    conn.close()
    print("\n🔌 Conexión cerrada")

# ========================================
# 4. FUNCIÓN DE VERIFICACIÓN RÁPIDA
# ========================================

def verificar_conexion():
    """Función para solo verificar la conexión sin hacer cambios"""
    
    print("🔍 VERIFICACIÓN DE CONEXIÓN")
    print("-" * 40)
    
    conn = conectar_bd()
    if conn:
        cursor = conn.cursor()
        
        try:
            # Test básico
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ PostgreSQL: {version.split(',')[0]}")
            
            # Verificar tabla usuarios
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'usuarios'
                )
            """)
            
            existe_tabla = cursor.fetchone()[0]
            print(f"✅ Tabla usuarios: {'Existe' if existe_tabla else 'No existe'}")
            
            if existe_tabla:
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                total = cursor.fetchone()[0]
                print(f"✅ Total usuarios: {total}")
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
        
        conn.close()
    else:
        print("❌ No se pudo conectar")

# ========================================
# 5. EJECUCIÓN
# ========================================

if __name__ == "__main__":
    print("🚀 Script de Reset de Usuarios")
    print("Selecciona una opción:")
    print("1. Ejecutar reset completo (ELIMINA todos los usuarios)")
    print("2. Solo verificar conexión")
    print("3. Salir")
    
    opcion = input("\nOpción (1-3): ").strip()
    
    if opcion == "1":
        main()
    elif opcion == "2":
        verificar_conexion()
    elif opcion == "3":
        print("👋 Saliendo...")
    else:
        print("❌ Opción inválida")
        sys.exit(1)