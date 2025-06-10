#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================
# CREAR USUARIO CON PSYCOPG2 DIRECTO
# Evita problemas de encoding usando conexión nativa
# ========================================

import os
import hashlib
import secrets
from datetime import datetime

def crear_conexion_nativa():
    """Crear conexión usando psycopg2 directamente"""
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        if DATABASE_URL:
            # Conexión Railway/producción
            conn = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=RealDictCursor
            )
        else:
            # Conexión local
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'normalizacion_db'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'admin'),
                cursor_factory=RealDictCursor
            )
        
        # Configurar encoding explícitamente
        conn.set_client_encoding('UTF8')
        
        return conn
    
    except ImportError:
        print("❌ psycopg2 no instalado")
        print("💡 Ejecuta: pip install psycopg2-binary")
        return None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def crear_usuario_directo_psycopg2():
    """Crear usuario usando psycopg2 directo para evitar problemas de encoding"""
    
    print("🎯 CREANDO USUARIO CON PSYCOPG2 DIRECTO")
    print("=" * 40)
    
    conn = crear_conexion_nativa()
    if not conn:
        return None, None
    
    try:
        cursor = conn.cursor()
        
        # Datos del usuario
        username = "admin_final"
        email = "admin_final@empresa.com"
        password = "Admin123!"  # Cumple todos los requisitos
        nombre_completo = "Administrador Final"
        rol = "SUPERUSUARIO"
        
        # Generar hash como lo hace el sistema
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        
        print(f"👤 Usuario: {username}")
        print(f"🔑 Contraseña: {password}")
        print(f"📧 Email: {email}")
        print(f"🎭 Rol: {rol}")
        
        # Eliminar usuario si existe
        cursor.execute("DELETE FROM usuarios WHERE username = %s", (username,))
        
        # Insertar nuevo usuario
        insert_sql = """
            INSERT INTO usuarios (
                username, email, password_hash, salt, nombre_completo, rol, activo,
                telefono, departamento, notificaciones_activas, tema_preferido, 
                idioma_preferido, fecha_creacion, intentos_fallidos, 
                fecha_ultimo_cambio_password
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        cursor.execute(insert_sql, (
            username,
            email,
            password_hash,
            salt,
            nombre_completo,
            rol,
            True,  # activo
            '555-FINAL',  # telefono
            'TI',  # departamento
            True,  # notificaciones_activas
            'claro',  # tema_preferido
            'es',  # idioma_preferido
            datetime.now(),  # fecha_creacion
            0,  # intentos_fallidos
            datetime.now()  # fecha_ultimo_cambio_password
        ))
        
        conn.commit()
        
        print("✅ Usuario insertado exitosamente")
        
        # Verificar inserción
        cursor.execute("SELECT username, rol, activo FROM usuarios WHERE username = %s", (username,))
        resultado = cursor.fetchone()
        
        if resultado:
            print(f"✅ Usuario verificado: {resultado['username']} ({resultado['rol']})")
            return username, password
        else:
            print("❌ Usuario no encontrado después de insertar")
            return None, None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return None, None
    
    finally:
        cursor.close()
        conn.close()

def listar_usuarios_psycopg2():
    """Listar usuarios usando psycopg2 para evitar problemas de encoding"""
    
    print("👥 LISTANDO USUARIOS CON PSYCOPG2")
    print("=" * 30)
    
    conn = crear_conexion_nativa()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Consulta simple
        cursor.execute("""
            SELECT username, rol, activo, email
            FROM usuarios 
            WHERE activo = true
            ORDER BY username
        """)
        
        usuarios = cursor.fetchall()
        
        print(f"📊 Usuarios encontrados ({len(usuarios)}):")
        
        for usuario in usuarios:
            estado = "🟢" if usuario['activo'] else "🔴"
            print(f"   {estado} {usuario['username']} ({usuario['rol']}) - {usuario['email']}")
        
        return [(u['username'], u['rol']) for u in usuarios]
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    
    finally:
        cursor.close()
        conn.close()

def probar_autenticacion_manual():
    """Probar autenticación manual con hash directo"""
    
    print("\n🧪 PROBANDO AUTENTICACIÓN MANUAL")
    print("=" * 30)
    
    conn = crear_conexion_nativa()
    if not conn:
        return None, None
    
    try:
        cursor = conn.cursor()
        
        # Obtener usuarios para probar
        cursor.execute("SELECT username, password_hash, salt FROM usuarios WHERE activo = true")
        usuarios = cursor.fetchall()
        
        # Contraseñas comunes para probar
        passwords_comunes = ['Admin123!', 'admin123', 'admin', '123', 'password']
        
        for usuario in usuarios:
            username = usuario['username']
            stored_hash = usuario['password_hash']
            stored_salt = usuario['salt']
            
            for password in passwords_comunes:
                # Probar diferentes métodos de hash
                hash_methods = [
                    hashlib.sha256((password + stored_salt).encode('utf-8')).hexdigest(),
                    hashlib.sha256((stored_salt + password).encode('utf-8')).hexdigest(),
                    hashlib.sha256(password.encode('utf-8')).hexdigest(),
                    hashlib.md5((password + stored_salt).encode('utf-8')).hexdigest()
                ]
                
                for hash_calculado in hash_methods:
                    if hash_calculado == stored_hash:
                        print(f"🎉 ¡CREDENCIALES VÁLIDAS!")
                        print(f"👤 Usuario: {username}")
                        print(f"🔑 Contraseña: {password}")
                        return username, password
        
        print("❌ No se encontraron credenciales válidas")
        return None, None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
    
    finally:
        cursor.close()
        conn.close()

def crear_multiples_usuarios_prueba():
    """Crear múltiples usuarios con diferentes métodos de hash"""
    
    print("\n🚀 CREANDO MÚLTIPLES USUARIOS DE PRUEBA")
    print("=" * 40)
    
    conn = crear_conexion_nativa()
    if not conn:
        return []
    
    usuarios_creados = []
    
    try:
        cursor = conn.cursor()
        
        # Diferentes combinaciones de usuario/contraseña/método
        usuarios_data = [
            {
                'username': 'test_simple',
                'password': 'admin123',
                'hash_method': lambda p, s: hashlib.sha256(p.encode()).hexdigest(),
                'salt': ''
            },
            {
                'username': 'test_salt',
                'password': 'admin123',
                'hash_method': lambda p, s: hashlib.sha256((p + s).encode()).hexdigest(),
                'salt': 'testsalt'
            },
            {
                'username': 'test_complejo',
                'password': 'Admin123!',
                'hash_method': lambda p, s: hashlib.sha256((p + s).encode()).hexdigest(),
                'salt': secrets.token_hex(16)
            },
            {
                'username': 'admin_simple',
                'password': 'admin12345',
                'hash_method': lambda p, s: hashlib.sha256((p + s).encode()).hexdigest(),
                'salt': 'admin_salt'
            }
        ]
        
        for user_data in usuarios_data:
            try:
                username = user_data['username']
                password = user_data['password']
                salt = user_data['salt']
                password_hash = user_data['hash_method'](password, salt)
                
                # Eliminar si existe
                cursor.execute("DELETE FROM usuarios WHERE username = %s", (username,))
                
                # Insertar
                cursor.execute("""
                    INSERT INTO usuarios (
                        username, email, password_hash, salt, nombre_completo, rol, activo
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    username,
                    f"{username}@test.com",
                    password_hash,
                    salt,
                    f"Usuario {username}",
                    'SUPERUSUARIO',
                    True
                ))
                
                usuarios_creados.append((username, password))
                print(f"✅ {username} creado (contraseña: {password})")
            
            except Exception as e:
                print(f"❌ Error creando {user_data['username']}: {e}")
        
        conn.commit()
        
        print(f"\n🎉 {len(usuarios_creados)} usuarios creados exitosamente")
        return usuarios_creados
    
    except Exception as e:
        print(f"❌ Error general: {e}")
        conn.rollback()
        return []
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🎯 CREADOR DE USUARIOS PSYCOPG2 DIRECTO")
    print("=" * 40)
    
    # Paso 1: Listar usuarios actuales
    print("PASO 1: Listando usuarios actuales...")
    usuarios_actuales = listar_usuarios_psycopg2()
    
    # Paso 2: Crear usuario principal
    print("\nPASO 2: Creando usuario principal...")
    username_principal, password_principal = crear_usuario_directo_psycopg2()
    
    # Paso 3: Crear usuarios de prueba
    print("\nPASO 3: Creando usuarios de prueba...")
    usuarios_prueba = crear_multiples_usuarios_prueba()
    
    # Paso 4: Probar autenticación manual
    print("\nPASO 4: Probando autenticación manual...")
    username_valido, password_valido = probar_autenticacion_manual()
    
    # Paso 5: Listar usuarios finales
    print("\nPASO 5: Listando usuarios finales...")
    usuarios_finales = listar_usuarios_psycopg2()
    
    # Resumen
    print("\n🎯 RESUMEN DE CREDENCIALES:")
    print("=" * 30)
    
    if username_principal and password_principal:
        print(f"✅ Usuario principal: {username_principal} / {password_principal}")
    
    if username_valido and password_valido:
        print(f"✅ Usuario validado: {username_valido} / {password_valido}")
    
    if usuarios_prueba:
        print("✅ Usuarios de prueba:")
        for username, password in usuarios_prueba:
            print(f"   👤 {username} / 🔑 {password}")
    
    print("\n🚀 PRUEBA ESTAS CREDENCIALES EN:")
    print("   streamlit run sistema_asincrono_normalizacion.py")