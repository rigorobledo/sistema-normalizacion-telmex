#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================
# CREAR USUARIO VÍA SISTEMA DIRECTAMENTE
# Usa las funciones exactas del sistema para crear usuario
# ========================================

import os
import sys

def crear_usuario_con_sistema():
    """Crear usuario usando las funciones exactas del sistema asíncrono"""
    
    print("🎯 CREANDO USUARIO VÍA SISTEMA ASÍNCRONO")
    print("=" * 40)
    
    try:
        # Importar todo lo necesario del sistema asíncrono
        sys.path.append('.')
        sys.path.append('modulos')
        
        # Importar sistema base
        from sistema_completo_normalizacion import SistemaNormalizacion
        
        # Importar autenticación mejorada
        from modulos.auth_mejorado import GestorUsuariosMejorado, crear_tabla_usuarios_mejorada
        
        print("✅ Módulos importados correctamente")
        
        # Crear instancia del sistema
        sistema = SistemaNormalizacion()
        print("✅ Sistema de normalización inicializado")
        
        # Crear/verificar tabla de usuarios mejorada
        crear_tabla_usuarios_mejorada(sistema.engine)
        print("✅ Tabla de usuarios verificada")
        
        # Crear gestor de usuarios
        gestor = GestorUsuariosMejorado(sistema.engine)
        print("✅ Gestor de usuarios creado")
        
        # Datos del nuevo usuario
        usuario_data = {
            'username': 'admin_sistema',
            'email': 'admin_sistema@empresa.com',
            'password': 'admin123',
            'nombre_completo': 'Administrador del Sistema',
            'rol': 'SUPERUSUARIO',
            'telefono': '555-SIST',
            'departamento': 'TI',
            'activo': True
        }
        
        # Crear usuario usando el método del gestor
        print("🚀 Creando usuario con método del sistema...")
        
        if hasattr(gestor, 'crear_usuario'):
            # El método requiere argumentos específicos, no un diccionario
            resultado = gestor.crear_usuario(
                username=usuario_data['username'],
                email=usuario_data['email'],
                password=usuario_data['password'],
                nombre_completo=usuario_data['nombre_completo'],
                rol=usuario_data['rol'],
                telefono=usuario_data.get('telefono'),
                departamento=usuario_data.get('departamento')
            )
            print("✅ Método crear_usuario usado")
        elif hasattr(gestor, 'create_user'):
            resultado = gestor.create_user(usuario_data)
            print("✅ Método create_user usado")
        else:
            # Buscar otros métodos
            metodos_usuario = [m for m in dir(gestor) if 'user' in m.lower() or 'usuario' in m.lower()]
            print(f"📋 Métodos disponibles: {metodos_usuario}")
            
            # Intentar método manual pero usando las funciones del gestor
            if hasattr(gestor, 'hash_password') or hasattr(gestor, 'crear_hash'):
                print("🔧 Usando método manual con funciones del gestor...")
                
                # Usar función de hash del gestor
                if hasattr(gestor, 'hash_password'):
                    password_hash, salt = gestor.hash_password(usuario_data['password'])
                elif hasattr(gestor, 'crear_hash'):
                    password_hash, salt = gestor.crear_hash(usuario_data['password'])
                else:
                    # Método de fallback
                    import hashlib
                    import secrets
                    salt = secrets.token_hex(16)
                    password_hash = hashlib.sha256((usuario_data['password'] + salt).encode()).hexdigest()
                
                # Insertar usando SQLAlchemy
                from sqlalchemy import text
                with sistema.engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO usuarios (
                            username, email, password_hash, salt, nombre_completo,
                            rol, activo, telefono, departamento
                        ) VALUES (
                            :username, :email, :password_hash, :salt, :nombre_completo,
                            :rol, :activo, :telefono, :departamento
                        )
                    """), {
                        'username': usuario_data['username'],
                        'email': usuario_data['email'],
                        'password_hash': password_hash,
                        'salt': salt,
                        'nombre_completo': usuario_data['nombre_completo'],
                        'rol': usuario_data['rol'],
                        'activo': usuario_data['activo'],
                        'telefono': usuario_data['telefono'],
                        'departamento': usuario_data['departamento']
                    })
                    conn.commit()
                
                resultado = True
                print("✅ Usuario creado con método manual")
            else:
                print("❌ No se encontraron métodos para crear usuario")
                return False
        
        if resultado:
            print("🎉 ¡Usuario creado exitosamente!")
            print(f"👤 Usuario: {usuario_data['username']}")
            print(f"🔑 Contraseña: {usuario_data['password']}")
            print(f"🎭 Rol: {usuario_data['rol']}")
            print()
            print("🎯 Prueba estas credenciales en el sistema asíncrono")
            
            # Verificar que el usuario se puede autenticar
            if hasattr(gestor, 'verificar_usuario'):
                print("\n🧪 Verificando autenticación...")
                if gestor.verificar_usuario(usuario_data['username'], usuario_data['password']):
                    print("✅ ¡Autenticación verificada!")
                else:
                    print("❌ Error en autenticación")
            
            return True
        else:
            print("❌ Error creando usuario")
            return False
    
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Verifica que todos los archivos estén en su lugar")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔍 Tipo de error: {type(e).__name__}")
        return False

def verificar_usuario_existente_con_sistema():
    """Verificar usuarios existentes usando el sistema"""
    
    print("🔍 VERIFICANDO USUARIOS CON SISTEMA")
    print("=" * 35)
    
    try:
        sys.path.append('.')
        sys.path.append('modulos')
        
        from sistema_completo_normalizacion import SistemaNormalizacion
        from modulos.auth_mejorado import GestorUsuariosMejorado
        
        sistema = SistemaNormalizacion()
        gestor = GestorUsuariosMejorado(sistema.engine)
        
        # Probar usuarios conocidos con contraseñas comunes
        usuarios_probar = ['admin', 'administrador', 'gerente', 'usuario']
        passwords_probar = ['admin123', 'admin', '123', 'password', 'gerente123', 'usuario123']
        
        print("🧪 Probando combinaciones conocidas...")
        
        for username in usuarios_probar:
            for password in passwords_probar:
                try:
                    if hasattr(gestor, 'verificar_usuario'):
                        if gestor.verificar_usuario(username, password):
                            print(f"🎉 ¡ÉXITO! {username} / {password}")
                            return username, password
                    elif hasattr(gestor, 'authenticate'):
                        if gestor.authenticate(username, password):
                            print(f"🎉 ¡ÉXITO! {username} / {password}")
                            return username, password
                except:
                    pass
        
        print("❌ No se encontraron credenciales válidas")
        return None, None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

if __name__ == "__main__":
    print("🎯 CREADOR DE USUARIO VÍA SISTEMA ASÍNCRONO")
    print("=" * 45)
    
    print("Opción 1: Crear nuevo usuario usando el sistema")
    print("Opción 2: Verificar usuarios existentes")
    
    opcion = input("\nSelecciona opción (1-2): ").strip()
    
    if opcion == "1":
        if crear_usuario_con_sistema():
            print("\n✅ ¡Usuario creado! Prueba el login ahora")
        else:
            print("\n❌ No se pudo crear usuario")
    
    elif opcion == "2":
        username, password = verificar_usuario_existente_con_sistema()
        if username and password:
            print(f"\n🎉 ¡Credenciales encontradas!")
            print(f"👤 Usuario: {username}")
            print(f"🔑 Contraseña: {password}")
        else:
            print("\n❌ No se encontraron credenciales válidas")
    
    else:
        print("❌ Opción inválida")