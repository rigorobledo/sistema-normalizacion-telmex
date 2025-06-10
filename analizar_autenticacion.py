#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================
# ANALIZADOR DE AUTENTICACIÓN
# Descubre exactamente cómo funciona el hash del sistema
# ========================================

import os
import sys
import hashlib
import secrets

def analizar_modulo_auth():
    """Analizar el módulo de autenticación del sistema asíncrono"""
    
    print("🔍 ANALIZANDO MÓDULO DE AUTENTICACIÓN")
    print("=" * 40)
    
    try:
        # Intentar importar el módulo de autenticación
        sys.path.append('modulos')
        from auth_mejorado import GestorUsuariosMejorado
        
        print("✅ Módulo auth_mejorado importado exitosamente")
        
        # Buscar métodos relacionados con hash
        gestor_methods = [method for method in dir(GestorUsuariosMejorado) if 'hash' in method.lower() or 'password' in method.lower() or 'verify' in method.lower()]
        
        print(f"🔍 Métodos relacionados con autenticación: {gestor_methods}")
        
        # Intentar encontrar el código fuente
        import inspect
        try:
            source = inspect.getsource(GestorUsuariosMejorado)
            print("📋 CÓDIGO FUENTE ENCONTRADO:")
            print("=" * 25)
            
            # Buscar líneas que contengan hash o password
            lines = source.split('\n')
            for i, line in enumerate(lines):
                if any(keyword in line.lower() for keyword in ['hash', 'password', 'salt', 'sha256', 'md5']):
                    print(f"{i+1:3d}: {line}")
        
        except Exception as e:
            print(f"❌ No se pudo obtener código fuente: {e}")
        
        return True
    
    except ImportError as e:
        print(f"❌ No se pudo importar auth_mejorado: {e}")
        return False
    except Exception as e:
        print(f"❌ Error analizando módulo: {e}")
        return False

def buscar_archivo_auth():
    """Buscar y leer el archivo de autenticación directamente"""
    
    print("📁 BUSCANDO ARCHIVO DE AUTENTICACIÓN")
    print("=" * 35)
    
    posibles_rutas = [
        'modulos/auth_mejorado.py',
        'auth_mejorado.py',
        './modulos/auth_mejorado.py',
        '../modulos/auth_mejorado.py'
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            print(f"✅ Archivo encontrado: {ruta}")
            
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                print("🔍 BUSCANDO FUNCIONES DE HASH:")
                print("=" * 30)
                
                # Buscar líneas relevantes
                lines = contenido.split('\n')
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['def hash', 'def verify', 'hashlib', 'sha256', 'password_hash', 'def crear_hash']):
                        # Mostrar contexto (líneas anteriores y posteriores)
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        
                        print(f"\nLíneas {start+1}-{end}:")
                        for j in range(start, end):
                            marker = ">>> " if j == i else "    "
                            print(f"{marker}{j+1:3d}: {lines[j]}")
                
                return contenido
            
            except Exception as e:
                print(f"❌ Error leyendo archivo {ruta}: {e}")
    
    print("❌ No se encontró el archivo de autenticación")
    return None

def crear_usuario_con_metodo_correcto():
    """Crear usuario usando el método exacto del sistema"""
    
    print("🎯 CREANDO USUARIO CON MÉTODO CORRECTO")
    print("=" * 35)
    
    # Intentar descubrir el método correcto analizando el código
    contenido_auth = buscar_archivo_auth()
    
    if contenido_auth:
        print("\n🔍 ANALIZANDO MÉTODO DE HASH...")
        
        # Buscar patrones comunes de hash
        if 'sha256(' in contenido_auth.lower():
            if '+ salt' in contenido_auth:
                metodo = "SHA256(password + salt)"
            elif 'salt +' in contenido_auth:
                metodo = "SHA256(salt + password)"
            else:
                metodo = "SHA256(password)"
        elif 'md5(' in contenido_auth.lower():
            metodo = "MD5"
        else:
            metodo = "DESCONOCIDO"
        
        print(f"🔒 Método detectado: {metodo}")
    
    # Probar diferentes métodos conocidos
    metodos_probar = [
        ("SHA256(password + salt)", lambda p, s: hashlib.sha256((p + s).encode()).hexdigest()),
        ("SHA256(salt + password)", lambda p, s: hashlib.sha256((s + p).encode()).hexdigest()),
        ("SHA256(password)", lambda p, s: hashlib.sha256(p.encode()).hexdigest()),
        ("MD5(password + salt)", lambda p, s: hashlib.md5((p + s).encode()).hexdigest()),
        ("MD5(password)", lambda p, s: hashlib.md5(p.encode()).hexdigest()),
    ]
    
    try:
        from sqlalchemy import create_engine, text
        
        # Conexión
        DATABASE_URL = os.getenv('DATABASE_URL')
        if DATABASE_URL:
            engine = create_engine(DATABASE_URL)
        else:
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            database = os.getenv('DB_NAME', 'normalizacion_db')
            username = os.getenv('DB_USER', 'postgres')
            password_db = os.getenv('DB_PASSWORD', 'admin')
            
            connection_string = f"postgresql://{username}:{password_db}@{host}:{port}/{database}"
            engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Crear usuarios con diferentes métodos
            for i, (nombre_metodo, func_hash) in enumerate(metodos_probar, 1):
                username = f"test_metodo_{i}"
                password = "test123"
                salt = "testsalt123"
                
                try:
                    # Calcular hash
                    if 'salt' in nombre_metodo.lower():
                        password_hash = func_hash(password, salt)
                    else:
                        password_hash = func_hash(password, "")
                        salt = ""
                    
                    # Eliminar usuario si existe
                    conn.execute(text(f"DELETE FROM usuarios WHERE username = '{username}'"))
                    
                    # Insertar usuario
                    conn.execute(text("""
                        INSERT INTO usuarios (
                            username, email, password_hash, salt, nombre_completo, rol, activo
                        ) VALUES (
                            :username, :email, :password_hash, :salt, :nombre_completo, :rol, :activo
                        )
                    """), {
                        'username': username,
                        'email': f'{username}@test.com',
                        'password_hash': password_hash,
                        'salt': salt,
                        'nombre_completo': f'Test {nombre_metodo}',
                        'rol': 'SUPERUSUARIO',
                        'activo': True
                    })
                    
                    print(f"✅ {username} creado con {nombre_metodo}")
                    print(f"   🔑 Contraseña: {password}")
                    print(f"   🧂 Salt: {salt}")
                    print(f"   🔒 Hash: {password_hash[:20]}...")
                    print()
                
                except Exception as e:
                    print(f"❌ Error creando {username}: {e}")
            
            conn.commit()
            
            print("🎯 USUARIOS DE PRUEBA CREADOS:")
            print("=" * 30)
            print("Prueba estos usuarios en el sistema:")
            for i in range(1, len(metodos_probar) + 1):
                print(f"👤 test_metodo_{i} / 🔑 test123")
            
            return True
    
    except Exception as e:
        print(f"❌ Error creando usuarios de prueba: {e}")
        return False

def simular_proceso_login():
    """Simular el proceso de login para entender cómo funciona"""
    
    print("🧪 SIMULANDO PROCESO DE LOGIN")
    print("=" * 30)
    
    try:
        # Intentar usar las funciones del sistema directamente
        sys.path.append('modulos')
        from auth_mejorado import GestorUsuariosMejorado
        
        # Obtener conexión
        from sqlalchemy import create_engine
        DATABASE_URL = os.getenv('DATABASE_URL')
        if DATABASE_URL:
            engine = create_engine(DATABASE_URL)
        else:
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            database = os.getenv('DB_NAME', 'normalizacion_db')
            username = os.getenv('DB_USER', 'postgres')
            password_db = os.getenv('DB_PASSWORD', 'admin')
            
            connection_string = f"postgresql://{username}:{password_db}@{host}:{port}/{database}"
            engine = create_engine(connection_string)
        
        gestor = GestorUsuariosMejorado(engine)
        
        # Buscar método de verificación
        if hasattr(gestor, 'verificar_usuario'):
            print("✅ Método verificar_usuario encontrado")
            
            # Intentar verificar con usuarios de prueba
            usuarios_probar = ['admin', 'acceso1', 'acceso2', 'acceso3', 'test_metodo_1']
            passwords_probar = ['admin123', 'hello', '123', 'admin', 'test123']
            
            for username in usuarios_probar:
                for password in passwords_probar:
                    try:
                        resultado = gestor.verificar_usuario(username, password)
                        if resultado:
                            print(f"🎉 ¡ÉXITO! Usuario: {username}, Contraseña: {password}")
                            return username, password
                        else:
                            print(f"❌ Falló: {username} / {password}")
                    except Exception as e:
                        print(f"⚠️ Error verificando {username}/{password}: {e}")
        
        elif hasattr(gestor, 'authenticate'):
            print("✅ Método authenticate encontrado")
            # Similar proceso con authenticate
        
        else:
            print("❌ No se encontró método de verificación")
            
            # Mostrar todos los métodos disponibles
            metodos = [m for m in dir(gestor) if not m.startswith('_')]
            print(f"📋 Métodos disponibles: {metodos}")
    
    except Exception as e:
        print(f"❌ Error simulando login: {e}")
    
    return None, None

def menu_analizador():
    """Menú del analizador"""
    
    print("\n🔍 ANALIZADOR DE AUTENTICACIÓN")
    print("=" * 30)
    print("1. 🔍 Analizar módulo de autenticación")
    print("2. 📁 Buscar archivo de autenticación")
    print("3. 🎯 Crear usuarios con método correcto")
    print("4. 🧪 Simular proceso de login")
    print("5. ❌ Salir")
    print()

if __name__ == "__main__":
    print("🔍 ANALIZADOR DE AUTENTICACIÓN DEL SISTEMA ASÍNCRONO")
    print("=" * 55)
    
    while True:
        try:
            menu_analizador()
            opcion = input("Selecciona opción (1-5): ").strip()
            print()
            
            if opcion == "1":
                analizar_modulo_auth()
            
            elif opcion == "2":
                buscar_archivo_auth()
            
            elif opcion == "3":
                crear_usuario_con_metodo_correcto()
            
            elif opcion == "4":
                username, password = simular_proceso_login()
                if username and password:
                    print(f"\n🎉 ¡Credenciales encontradas!")
                    print(f"👤 Usuario: {username}")
                    print(f"🔑 Contraseña: {password}")
                    break
            
            elif opcion == "5":
                print("👋 ¡Hasta luego!")
                break
            
            else:
                print("❌ Opción inválida")
            
            print("\n" + "="*50)
            input("Presiona Enter para continuar...")
            print()
        
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")