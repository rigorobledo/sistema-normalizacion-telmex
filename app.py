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


import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Detectar ambiente
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
IS_LOCAL = not IS_RAILWAY


# ========================================
# SISTEMA COMPLETO DE LOGIN Y AUTENTICACIÓN
# AGREGAR AL INICIO DEL ARCHIVO (después de los imports)
# ========================================

import hashlib
import secrets
from datetime import datetime, timedelta

# ========================================
# 1. TABLA DE USUARIOS - AGREGAR A crear_tablas_sistema()
# ========================================

def crear_tabla_usuarios(engine):
    """Crear tabla de usuarios con roles"""
    
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
        creado_por UUID REFERENCES usuarios(id_usuario),
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
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql_usuarios))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error creando tabla usuarios: {e}")
        return False

# ========================================
# 2. CLASE DE GESTIÓN DE USUARIOS
# ========================================

class GestorUsuarios:
    """Clase para manejar autenticación y usuarios"""
    
    def __init__(self, engine):
        self.engine = engine
    
    def generar_hash_password(self, password):
        """Generar hash seguro de contraseña"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                           password.encode('utf-8'), 
                                           salt.encode('utf-8'), 
                                           100000)
        return password_hash.hex(), salt
    
    def verificar_password(self, password, password_hash, salt):
        """Verificar contraseña"""
        new_hash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt.encode('utf-8'), 
                                      100000)
        return new_hash.hex() == password_hash
    
    def crear_usuario(self, username, email, password, nombre_completo, rol='USUARIO', creado_por=None):
        """Crear nuevo usuario"""
        try:
            # Validaciones
            if len(username) < 3:
                return False, "El username debe tener al menos 3 caracteres"
            
            if len(password) < 6:
                return False, "La contraseña debe tener al menos 6 caracteres"
            
            # Verificar si ya existe
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM usuarios 
                    WHERE username = :username OR email = :email
                """), {'username': username, 'email': email})
                
                if result.fetchone()[0] > 0:
                    return False, "Usuario o email ya existe"
                
                # Crear hash de contraseña
                password_hash, salt = self.generar_hash_password(password)
                
                # Insertar usuario
                conn.execute(text("""
                    INSERT INTO usuarios (username, email, password_hash, salt, nombre_completo, rol, creado_por)
                    VALUES (:username, :email, :password_hash, :salt, :nombre_completo, :rol, :creado_por)
                """), {
                    'username': username,
                    'email': email,
                    'password_hash': password_hash,
                    'salt': salt,
                    'nombre_completo': nombre_completo,
                    'rol': rol,
                    'creado_por': creado_por
                })
                
                conn.commit()
                return True, "Usuario creado exitosamente"
        
        except Exception as e:
            return False, f"Error creando usuario: {str(e)}"
    
    def autenticar_usuario(self, username, password):
        """Autenticar usuario"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id_usuario, username, email, password_hash, salt, 
                           nombre_completo, rol, activo, intentos_fallidos, bloqueado_hasta
                    FROM usuarios 
                    WHERE username = :username AND activo = true
                """), {'username': username})
                
                user_row = result.fetchone()
                
                if not user_row:
                    return False, None, "Usuario no encontrado o inactivo"
                
                user_data = dict(user_row._mapping)
                
                # Verificar si está bloqueado
                if user_data['bloqueado_hasta'] and user_data['bloqueado_hasta'] > datetime.now():
                    return False, None, f"Usuario bloqueado hasta {user_data['bloqueado_hasta']}"
                
                # Verificar contraseña
                if self.verificar_password(password, user_data['password_hash'], user_data['salt']):
                    # Login exitoso - resetear intentos fallidos
                    conn.execute(text("""
                        UPDATE usuarios 
                        SET fecha_ultimo_acceso = CURRENT_TIMESTAMP, intentos_fallidos = 0, bloqueado_hasta = NULL
                        WHERE id_usuario = :id_usuario
                    """), {'id_usuario': user_data['id_usuario']})
                    
                    conn.commit()
                    
                    # Remover datos sensibles
                    del user_data['password_hash']
                    del user_data['salt']
                    
                    return True, user_data, "Login exitoso"
                else:
                    # Incrementar intentos fallidos
                    new_attempts = user_data['intentos_fallidos'] + 1
                    bloqueo = None
                    
                    if new_attempts >= 5:
                        bloqueo = datetime.now() + timedelta(minutes=30)
                    
                    conn.execute(text("""
                        UPDATE usuarios 
                        SET intentos_fallidos = :intentos, bloqueado_hasta = :bloqueo
                        WHERE id_usuario = :id_usuario
                    """), {
                        'intentos': new_attempts,
                        'bloqueo': bloqueo,
                        'id_usuario': user_data['id_usuario']
                    })
                    
                    conn.commit()
                    
                    if bloqueo:
                        return False, None, "Demasiados intentos fallidos. Usuario bloqueado por 30 minutos"
                    else:
                        return False, None, f"Contraseña incorrecta. Intentos restantes: {5 - new_attempts}"
        
        except Exception as e:
            return False, None, f"Error en autenticación: {str(e)}"
    
    def crear_sesion(self, id_usuario, ip_address=None, user_agent=None):
        """Crear sesión de usuario"""
        try:
            token = secrets.token_urlsafe(64)
            fecha_expiracion = datetime.now() + timedelta(hours=8)  # 8 horas
            
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO sesiones_usuario (id_usuario, token_sesion, ip_address, user_agent, fecha_expiracion)
                    VALUES (:id_usuario, :token, :ip, :user_agent, :expiracion)
                """), {
                    'id_usuario': id_usuario,
                    'token': token,
                    'ip': ip_address,
                    'user_agent': user_agent,
                    'expiracion': fecha_expiracion
                })
                
                conn.commit()
                return token
        
        except Exception as e:
            print(f"Error creando sesión: {e}")
            return None
    
    def validar_sesion(self, token):
        """Validar sesión activa"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT u.id_usuario, u.username, u.email, u.nombre_completo, u.rol,
                           s.fecha_expiracion
                    FROM sesiones_usuario s
                    JOIN usuarios u ON s.id_usuario = u.id_usuario
                    WHERE s.token_sesion = :token AND s.activa = true AND s.fecha_expiracion > CURRENT_TIMESTAMP
                """), {'token': token})
                
                session_row = result.fetchone()
                
                if session_row:
                    return dict(session_row._mapping)
                else:
                    return None
        
        except Exception as e:
            print(f"Error validando sesión: {e}")
            return None
    
    def cerrar_sesion(self, token):
        """Cerrar sesión"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE sesiones_usuario 
                    SET activa = false 
                    WHERE token_sesion = :token
                """), {'token': token})
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"Error cerrando sesión: {e}")
            return False
    
    def listar_usuarios(self):
        """Listar todos los usuarios"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT u.id_usuario, u.username, u.email, u.nombre_completo, u.rol, 
                           u.activo, u.fecha_creacion, u.fecha_ultimo_acceso,
                           c.username as creado_por_username
                    FROM usuarios u
                    LEFT JOIN usuarios c ON u.creado_por = c.id_usuario
                    ORDER BY u.fecha_creacion DESC
                """))
                
                usuarios = []
                for row in result:
                    usuarios.append(dict(row._mapping))
                
                return usuarios
        
        except Exception as e:
            print(f"Error listando usuarios: {e}")
            return []

# ========================================
# 3. FUNCIONES DE LOGIN PARA STREAMLIT
# ========================================

def inicializar_sistema_usuarios():
    """Inicializar sistema de usuarios"""
    
    if 'gestor_usuarios' not in st.session_state:
        # Crear gestor de usuarios
        sistema = SistemaNormalizacion()
        st.session_state.gestor_usuarios = GestorUsuarios(sistema.engine)
        
        # Crear tabla de usuarios
        crear_tabla_usuarios(sistema.engine)
        
        # Crear superusuario por defecto si no existe
        crear_superusuario_default()

def crear_superusuario_default():
    """Crear superusuario por defecto"""
    
    gestor = st.session_state.gestor_usuarios
    
    try:
        with gestor.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM usuarios WHERE rol = 'SUPERUSUARIO'"))
            count = result.fetchone()[0]
            
            if count == 0:
                # Crear superusuario por defecto
                exito, mensaje = gestor.crear_usuario(
                    username='admin',
                    email='admin@telmex.com',
                    password='admin123',  # CAMBIAR EN PRODUCCIÓN
                    nombre_completo='Administrador del Sistema',
                    rol='SUPERUSUARIO'
                )
                
                if exito:
                    st.success("✅ Superusuario por defecto creado: admin/admin123")
                else:
                    st.error(f"Error creando superusuario: {mensaje}")
    
    except Exception as e:
        st.error(f"Error verificando superusuario: {e}")

def mostrar_pantalla_login():
    """Login con estructura similar al dashboard (con tabs)"""
    
    # HEADER IGUAL AL DASHBOARD
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        try:
            st.image("logo_RN.png", width=120)
        except:
            st.markdown("🏠")
    with col_title:
        st.markdown("""
        <div  style="text-align: left;">
            <h3>Red Nacional Última Milla</h3>
            <h5>Sistema Integral de Normalización Domicilios | Procesamiento Inteligente de Domicilios</h5>
        </div>
        """, unsafe_allow_html=True)
    
    # TABS COMO EL DASHBOARD
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "ℹ️ Información"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### 🔐 Acceso al Sistema")
            
            with st.form("login_form"):
                username = st.text_input("👤 Usuario:", placeholder="Ingresa tu usuario")
                password = st.text_input("🔒 Contraseña:", type="password", placeholder="Ingresa tu contraseña")
                
                login_button = st.form_submit_button("🚀 Ingresar", use_container_width=True, type="primary")
                
                if login_button:
                    if username and password:
                        gestor = st.session_state.gestor_usuarios
                        exito, user_data, mensaje = gestor.autenticar_usuario(username, password)
                        
                        if exito:
                            token = gestor.crear_sesion(user_data['id_usuario'])
                            
                            if token:
                                st.session_state.usuario_autenticado = True
                                st.session_state.usuario_actual = user_data
                                st.session_state.token_sesion = token
                                
                                st.success(f"¡Bienvenido, {user_data['nombre_completo']}!")
                                st.rerun()
                            else:
                                st.error("Error creando sesión")
                        else:
                            st.error(mensaje)
                    else:
                        st.warning("Por favor, ingresa usuario y contraseña")
    
    with tab2:
        st.markdown("### ℹ️ Información del Sistema")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🔑 Credenciales por Defecto:**
            - **Usuario:** admin
            - **Contraseña:** admin123
            
            **👥 Roles del Sistema:**
            - **SUPERUSUARIO:** Control total
            - **GERENTE:** Gestión avanzada  
            - **USUARIO:** Solo visualización
            """)
        
        with col2:
            st.markdown("""
            **🛡️ Características de Seguridad:**
            - Contraseñas cifradas
            - Bloqueo por intentos fallidos
            - Sesiones seguras (8 horas)
            - Auditoría de accesos
            
            **📞 Soporte:**
            - Contacta al administrador del sistema
            - Para problemas de acceso
            """)
        
        st.info("⚠️ **Importante:** Cambia la contraseña por defecto después del primer acceso por seguridad.")


def verificar_autenticacion():
    """Verificar si el usuario está autenticado"""
    
    if 'usuario_autenticado' not in st.session_state:
        st.session_state.usuario_autenticado = False
    
    if 'token_sesion' in st.session_state and st.session_state.token_sesion:
        # Validar sesión
        gestor = st.session_state.gestor_usuarios
        user_data = gestor.validar_sesion(st.session_state.token_sesion)
        
        if user_data:
            st.session_state.usuario_autenticado = True
            st.session_state.usuario_actual = user_data
            return True
        else:
            # Sesión expirada
            st.session_state.usuario_autenticado = False
            if 'usuario_actual' in st.session_state:
                del st.session_state.usuario_actual
            if 'token_sesion' in st.session_state:
                del st.session_state.token_sesion
            return False
    
    return st.session_state.usuario_autenticado

def cerrar_sesion():
    """Cerrar sesión del usuario"""
    
    if 'token_sesion' in st.session_state:
        gestor = st.session_state.gestor_usuarios
        gestor.cerrar_sesion(st.session_state.token_sesion)
    
    # Limpiar session_state
    st.session_state.usuario_autenticado = False
    if 'usuario_actual' in st.session_state:
        del st.session_state.usuario_actual
    if 'token_sesion' in st.session_state:
        del st.session_state.token_sesion
    
    st.rerun()

def es_superusuario():
    """Verificar si el usuario actual es superusuario"""
    if 'usuario_actual' in st.session_state:
        return st.session_state.usuario_actual.get('rol') in ['SUPERUSUARIO', 'GERENTE']
    return False

def mostrar_barra_usuario():
    """Mostrar barra de usuario autenticado"""
    
    if 'usuario_actual' in st.session_state:
        user = st.session_state.usuario_actual
        
        col1, col2, col3 = st.columns([6, 2, 1])
        
        with col1:
            rol_emoji = "👑" if user['rol'] == 'SUPERUSUARIO' else "👨‍💼" if user['rol'] == 'GERENTE' else "👤"
            st.markdown(f"**{rol_emoji} {user['nombre_completo']}** | {user['rol']}")
        
        with col2:
            if es_superusuario():
                if st.button("👥 Gestionar Usuarios", key="manage_users"):
                    st.session_state.mostrar_gestion_usuarios = True
        
        with col3:
            if st.button("🚪 Salir", key="logout"):
                cerrar_sesion()

# ========================================
# 4. GESTIÓN DE USUARIOS (SOLO SUPERUSUARIOS)
# ========================================

def mostrar_gestion_usuarios():
    """Interfaz de gestión de usuarios (solo para superusuarios)"""
    
    if not es_superusuario():
        st.error("❌ No tienes permisos para acceder a esta sección")
        return
    
    st.markdown("## 👥 Gestión de Usuarios")
    
    tab1, tab2 = st.tabs(["📋 Lista de Usuarios", "➕ Crear Usuario"])
    
    with tab1:
        mostrar_lista_usuarios()
    
    with tab2:
        mostrar_formulario_crear_usuario()

def mostrar_lista_usuarios():
    """Mostrar lista de usuarios"""
    
    gestor = st.session_state.gestor_usuarios
    usuarios = gestor.listar_usuarios()
    
    if usuarios:
        st.markdown("### 📊 Usuarios del Sistema")
        
        # Convertir a DataFrame para mostrar
        df_usuarios = pd.DataFrame(usuarios)
        
        # Preparar columnas para mostrar
        df_display = df_usuarios[['username', 'nombre_completo', 'email', 'rol', 'activo', 'fecha_ultimo_acceso']].copy()
        df_display['activo'] = df_display['activo'].apply(lambda x: "✅ Activo" if x else "❌ Inactivo")
        df_display['fecha_ultimo_acceso'] = pd.to_datetime(df_display['fecha_ultimo_acceso']).dt.strftime('%Y-%m-%d %H:%M')
        
        df_display.columns = ['Usuario', 'Nombre Completo', 'Email', 'Rol', 'Estado', 'Último Acceso']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Estadísticas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Usuarios", len(usuarios))
        
        with col2:
            activos = sum(1 for u in usuarios if u['activo'])
            st.metric("Usuarios Activos", activos)
        
        with col3:
            superusuarios = sum(1 for u in usuarios if u['rol'] in ['SUPERUSUARIO', 'GERENTE'])
            st.metric("Administradores", superusuarios)
        
        with col4:
            # Usuarios con acceso reciente (últimos 7 días)
            fecha_limite = datetime.now() - timedelta(days=7)
            recientes = sum(1 for u in usuarios if u['fecha_ultimo_acceso'] and 
                          pd.to_datetime(u['fecha_ultimo_acceso']) > fecha_limite)
            st.metric("Activos (7 días)", recientes)
    
    else:
        st.info("No hay usuarios registrados en el sistema")

def mostrar_formulario_crear_usuario():
    """Formulario para crear nuevo usuario"""
    
    st.markdown("### ➕ Crear Nuevo Usuario")
    
    with st.form("crear_usuario_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nuevo_username = st.text_input("👤 Usuario:", placeholder="ej: jperez")
            nuevo_email = st.text_input("📧 Email:", placeholder="usuario@telmex.com")
            nuevo_password = st.text_input("🔒 Contraseña:", type="password", 
                                         help="Mínimo 6 caracteres")
        
        with col2:
            nuevo_nombre = st.text_input("👨‍💼 Nombre Completo:", placeholder="Juan Pérez")
            nuevo_rol = st.selectbox("🎭 Rol:", 
                                   options=['USUARIO', 'GERENTE', 'SUPERUSUARIO'],
                                   help="USUARIO: Solo visualización\nGERENTE: Gestión básica\nSUPERUSUARIO: Control total")
        
        crear_usuario_button = st.form_submit_button("✅ Crear Usuario", type="primary")
        
        if crear_usuario_button:
            if all([nuevo_username, nuevo_email, nuevo_password, nuevo_nombre]):
                gestor = st.session_state.gestor_usuarios
                user_actual = st.session_state.usuario_actual
                
                exito, mensaje = gestor.crear_usuario(
                    username=nuevo_username,
                    email=nuevo_email,
                    password=nuevo_password,
                    nombre_completo=nuevo_nombre,
                    rol=nuevo_rol,
                    creado_por=user_actual['id_usuario']
                )
                
                if exito:
                    st.success(f"✅ Usuario '{nuevo_username}' creado exitosamente")
                    st.rerun()
                else:
                    st.error(f"❌ {mensaje}")
            else:
                st.warning("⚠️ Por favor, completa todos los campos")

# ========================================
# 5. INTEGRACIÓN CON EL MAIN EXISTENTE
# ========================================

def main_con_autenticacion():
    """Función main con autenticación integrada"""
    
    # Inicializar sistema de usuarios
    inicializar_sistema_usuarios()
    
    # Verificar autenticación
    if not verificar_autenticacion():
        mostrar_pantalla_login()
        return
    
    # Usuario autenticado - mostrar aplicación
    mostrar_barra_usuario()
    
    # Verificar si se debe mostrar gestión de usuarios
    if st.session_state.get('mostrar_gestion_usuarios', False):
        mostrar_gestion_usuarios()
        
        if st.button("⬅️ Volver al Dashboard"):
            st.session_state.mostrar_gestion_usuarios = False
            st.rerun()
        
        return
    
    # Aplicación principal existente
    main_aplicacion_original()

def main_aplicacion_original():
    """Tu función main() original - RENOMBRAR tu main() actual a esto"""
    
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
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        try:
            st.image("logo_RN.png", width=120)
        except:
            st.markdown("🏠")
    with col_title:
        st.markdown("""
        <div  style="text-align: left;">
            <h3>Red Nacional Última Milla</h3>
            <h5>Sistema Integral de Normalización Domicilios | Procesamiento Inteligente de Domicilios</h5>
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

# ========================================
# PASO 1: AGREGAR DICCIONARIOS INTELIGENTES
# ========================================

# INSTRUCCIONES:
# 1. Agregar este código AL INICIO de tu archivo Python, después de los imports
# 2. Luego agregar el método inicializar_diccionarios() a la clase SistemaNormalizacion
# 3. Llamar el método en __init__()

# ========================================
# DICCIONARIOS DE CONOCIMIENTO (AGREGAR AL INICIO DEL ARCHIVO)
# ========================================

# Configuración adaptativa de base de datos
if IS_RAILWAY:
    # En Railway: usar DATABASE_URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    # Railway da la URL completa, la parseamos después
    DATABASE_CONFIG = {'url': DATABASE_URL}
else:
    # Local: usar configuración original
    DATABASE_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'normalizacion_domicilios'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'admin123')
    }

# Diccionario de abreviaciones comunes en México
ABREVIACIONES_MEXICO = {
    # Estados más comunes
    'B.C.': 'BAJA CALIFORNIA',
    'B.C.S.': 'BAJA CALIFORNIA SUR',
    'CDMX': 'CIUDAD DE MEXICO',
    'D.F.': 'CIUDAD DE MEXICO',
    'DISTRITO FEDERAL': 'CIUDAD DE MEXICO',
    'EDO MEX': 'ESTADO DE MEXICO',
    'EDO. MEX.': 'ESTADO DE MEXICO',
    'MEX.': 'ESTADO DE MEXICO',
    'N.L.': 'NUEVO LEON',
    'Q.R.': 'QUINTANA ROO',
    'Q. ROO': 'QUINTANA ROO',
    'S.L.P.': 'SAN LUIS POTOSI',
    
    # Estados con abreviaciones típicas
    'COAH.': 'COAHUILA',
    'CHIH.': 'CHIHUAHUA',
    'CHIS.': 'CHIAPAS',
    'GTO.': 'GUANAJUATO',
    'GRO.': 'GUERRERO',
    'HGO.': 'HIDALGO',
    'JAL.': 'JALISCO',
    'MICH.': 'MICHOACAN',
    'MOR.': 'MORELOS',
    'NAY.': 'NAYARIT',
    'OAX.': 'OAXACA',
    'PUE.': 'PUEBLA',
    'QRO.': 'QUERETARO',
    'SIN.': 'SINALOA',
    'SON.': 'SONORA',
    'TAB.': 'TABASCO',
    'TAMS.': 'TAMAULIPAS',
    'TLAX.': 'TLAXCALA',
    'VER.': 'VERACRUZ',
    'YUC.': 'YUCATAN',
    'ZAC.': 'ZACATECAS',
    
    # Ciudades comunes
    'CD JUAREZ': 'CIUDAD JUAREZ',
    'CD. JUAREZ': 'CIUDAD JUAREZ',
    'GDLE': 'GUADALAJARA',
    'GDL': 'GUADALAJARA',
    'MTY': 'MONTERREY',
    
    # Prefijos y títulos comunes
    'CD.': 'CIUDAD',
    'STA.': 'SANTA',
    'STO.': 'SANTO',
    'S.': 'SAN',
    'GRAL.': 'GENERAL',
    'PRES.': 'PRESIDENTE',
    'PROF.': 'PROFESOR',
    'DR.': 'DOCTOR',
    'ING.': 'INGENIERO',
    'LIC.': 'LICENCIADO',
    'COL.': 'COLONIA',
    'FRACC.': 'FRACCIONAMIENTO',
    'DELEG.': 'DELEGACION',
    'MPIO.': 'MUNICIPIO'
}

# Correcciones de errores tipográficos comunes
CORRECCIONES_TIPOGRAFICAS = {
    # Números por letras (muy común en OCR y digitación)
    '0': 'O',  # Cero por O
    '1': 'I',  # Uno por I
    '3': 'E',  # Tres por E
    '5': 'S',  # Cinco por S
    
    # Letras similares
    'PH': 'F',
    'QU': 'C',
    'K': 'C',
    'W': 'V',
    'Y': 'I'
}

# Sinónimos y equivalencias
SINONIMOS_MEXICO = {
    'CENTRO': ['CENTRO HISTORICO', 'PRIMER CUADRO', 'ZOCALO', 'CENTRO HIST'],
    'INDUSTRIAL': ['ZONA INDUSTRIAL', 'PARQUE INDUSTRIAL', 'Z INDUSTRIAL'],
    'RESIDENCIAL': ['ZONA RESIDENCIAL', 'FRACCIONAMIENTO', 'FRACC'],
    'POPULAR': ['COLONIA POPULAR', 'BARRIO POPULAR', 'COL POPULAR'],
    'AMPLIACION': ['AMPL', 'AMPL.', 'AMPLIAC', 'AMPLIAC'],
    'FRACCIONAMIENTO': ['FRACC', 'FRACC.', 'FRAC', 'FRACCION'],
    'UNIDAD': ['UNID', 'U', 'CONJUNTO', 'CONJ'],
    'PRIVADA': ['PRIV', 'PRIV.', 'PRIVADO', 'PRIV'],
    'COLONIA': ['COL', 'COL.', 'BARRIO'],
    'DELEGACION': ['DELEG', 'DELEG.', 'DELEGAC']
}

# Patrones específicos para domicilios mexicanos
PATRONES_LIMPIEZA_MEXICO = [
    # Remover prefijos innecesarios comunes
    (r'^(LA |EL |LOS |LAS )', ''),
    (r'^(DE LA |DEL |DE LOS |DE LAS )', ''),
    
    # Normalizar espacios múltiples
    (r'\s+', ' '),
    
    # Remover caracteres especiales comunes en domicilios
    (r'[#°ªº]', ''),
    (r'[-_]', ' '),
    (r'[(){}[\]]', ''),
    
    # Números romanos comunes a números arábigos
    (r'\bI\b', '1'),
    (r'\bII\b', '2'),
    (r'\bIII\b', '3'),
    (r'\bIV\b', '4'),
    (r'\bV\b', '5'),
    (r'\bVI\b', '6'),
    (r'\bVII\b', '7'),
    (r'\bVIII\b', '8'),
    (r'\bIX\b', '9'),
    (r'\bX\b', '10'),
    
    # Normalizar separadores
    (r'[/\\|]', ' '),
    
    # Limpiar múltiples puntos
    (r'\.{2,}', '.')
]

# ========================================
# 1. CONFIGURACIÓN AVANZADA
# ========================================



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
        self.inicializar_diccionarios_inteligentes()
        self.inicializar_patrones_limpieza()
        
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

        crear_tabla_usuarios(self.engine)

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
        texto_limpio = self.limpiar_texto_inteligente(texto_original, tipo_catalogo)
        
        # Buscar en referencias
        referencia_encontrada = self.buscar_en_referencias_CORREGIDO(texto_limpio, tipo_catalogo)
        
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
    
    def limpiar_texto_inteligente(self, texto, tipo_catalogo=None):
        """Limpieza inteligente que reemplaza al método limpiar_texto() original"""
        
        if not isinstance(texto, str):
            return ""
        
        print(f"🧠 Limpieza inteligente: '{texto}' (tipo: {tipo_catalogo})")
        
        # PASO 1: Conversión básica
        texto_procesado = texto.upper().strip()
        print(f"   Mayúsculas: '{texto_procesado}'")
        
        # PASO 2: Expandir abreviaciones ANTES de limpiar
        if hasattr(self, 'expandir_abreviaciones_inteligente'):
            texto_expandido = self.expandir_abreviaciones_inteligente(texto_procesado)
            if texto_expandido != texto_procesado:
                print(f"   Expandido: '{texto_expandido}'")
                texto_procesado = texto_expandido
        
        # PASO 3: Correcciones tipográficas ANTES de limpiar
        if hasattr(self, 'corregir_errores_tipograficos'):
            texto_corregido = self.corregir_errores_tipograficos(texto_procesado)
            if texto_corregido != texto_procesado:
                print(f"   Corregido: '{texto_corregido}'")
                texto_procesado = texto_corregido
        
        # PASO 4: Aplicar patrones específicos de limpieza
        for patron, reemplazo in PATRONES_LIMPIEZA_MEXICO:
            texto_anterior = texto_procesado
            texto_procesado = re.sub(patron, reemplazo, texto_procesado)
            if texto_procesado != texto_anterior:
                print(f"   Patrón aplicado: '{texto_anterior}' → '{texto_procesado}'")
        
        # PASO 5: Quitar acentos (proceso original)
        texto_sin_acentos = unicodedata.normalize('NFD', texto_procesado)
        texto_sin_acentos = ''.join(char for char in texto_sin_acentos if unicodedata.category(char) != 'Mn')
        
        # PASO 6: Limpiar caracteres especiales (proceso original)  
        texto_limpio = re.sub(r'[^\w\s]', ' ', texto_sin_acentos)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        
        # PASO 7: Limpieza final específica por tipo de catálogo
        texto_final = self.limpieza_especifica_por_tipo(texto_limpio, tipo_catalogo)
        
        print(f"   Resultado final: '{texto_final}'")
        return texto_final
    
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
                nombre_ref_limpio = self.limpiar_texto_inteligente(ref['nombre_oficial'])
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
        
    def buscar_en_referencias_CORREGIDO(self, texto_limpio, tipo_catalogo):
        """
        Buscar coincidencias en las referencias usando IA - VERSIÓN CORREGIDA
        
        REEMPLAZAR EL MÉTODO EXISTENTE buscar_en_referencias() POR ESTE
        """
        
        print(f"🔍 Buscando: '{texto_limpio}' en {tipo_catalogo}")
        
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
                print(f"   ❌ No hay referencias para {tipo_catalogo}")
                return None
            
            print(f"   📊 Encontradas {len(referencias)} referencias para {tipo_catalogo}")
            
            # Buscar coincidencia exacta
            for ref in referencias:
                nombre_ref_limpio = ref['nombre_oficial'].upper().strip()
                if texto_limpio == nombre_ref_limpio:
                    print(f"   ✅ EXACTO: '{texto_limpio}' = '{nombre_ref_limpio}'")
                    return {
                        **ref,
                        'metodo': 'EXACTO',
                        'confianza': 1.0
                    }
            
            # Buscar con fuzzy matching - CORREGIDO
            nombres_referencias = [ref['nombre_oficial'].upper().strip() for ref in referencias]
            
            print(f"   🔍 Fuzzy: comparando '{texto_limpio}' con {len(nombres_referencias)} nombres")
            
            # Importar aquí para evitar problemas de importación
            from fuzzywuzzy import fuzz, process
            
            # Probar diferentes scorers
            mejor_fuzzy = process.extractOne(texto_limpio, nombres_referencias, scorer=fuzz.token_sort_ratio)
            
            print(f"   🎯 Mejor fuzzy: {mejor_fuzzy}")
            
            if mejor_fuzzy and mejor_fuzzy[1] >= 60:  # Umbral mínimo 60%
                # Encontrar la referencia correspondiente
                for ref in referencias:
                    nombre_ref = ref['nombre_oficial'].upper().strip()
                    if nombre_ref == mejor_fuzzy[0]:
                        print(f"   ✅ FUZZY: '{texto_limpio}' → '{nombre_ref}' ({mejor_fuzzy[1]}%)")
                        return {
                            **ref,
                            'metodo': 'FUZZY_ALTO' if mejor_fuzzy[1] >= 80 else 'FUZZY_BAJO',
                            'confianza': mejor_fuzzy[1] / 100.0
                        }
            
            print(f"   ❌ Sin coincidencias para '{texto_limpio}' (mejor score: {mejor_fuzzy[1] if mejor_fuzzy else 0}%)")
            return None
            
        except Exception as e:
            print(f"   ❌ Error buscando referencias: {e}")
            import traceback
            traceback.print_exc()
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

    def inicializar_diccionarios_inteligentes(self):
        """
        Método para agregar a la clase SistemaNormalizacion
        AGREGAR ESTE MÉTODO A TU CLASE EXISTENTE
        """
        
        print("🧠 Inicializando diccionarios inteligentes...")
        
        # Cargar diccionarios globales en la instancia
        self.abreviaciones = ABREVIACIONES_MEXICO.copy()
        self.correcciones = CORRECCIONES_TIPOGRAFICAS.copy()
        self.sinonimos = SINONIMOS_MEXICO.copy()
        
        print(f"   ✅ {len(self.abreviaciones)} abreviaciones cargadas")
        print(f"   ✅ {len(self.correcciones)} correcciones cargadas")
        print(f"   ✅ {len(self.sinonimos)} grupos de sinónimos cargados")
        
        # Crear índice inverso de sinónimos para búsqueda rápida
        self.indice_sinonimos = {}
        for principal, variaciones in self.sinonimos.items():
            for variacion in variaciones:
                self.indice_sinonimos[variacion] = principal
        
        print(f"   ✅ {len(self.indice_sinonimos)} sinónimos indexados")


    def expandir_abreviaciones_inteligente(self, texto):
        """
        Método para agregar a la clase SistemaNormalizacion
        AGREGAR ESTE MÉTODO A TU CLASE EXISTENTE
        """
        
        if not hasattr(self, 'abreviaciones'):
            return texto  # Si no están inicializados los diccionarios, devolver original
        
        texto_expandido = texto.upper().strip()
        expansiones_realizadas = []
        
        # Expandir abreviaciones exactas
        for abrev, completo in self.abreviaciones.items():
            if abrev in texto_expandido:
                texto_expandido = texto_expandido.replace(abrev, completo)
                expansiones_realizadas.append(f"{abrev} → {completo}")
        
        # Expandir sinónimos
        palabras = texto_expandido.split()
        palabras_expandidas = []
        
        for palabra in palabras:
            if palabra in self.indice_sinonimos:
                palabra_principal = self.indice_sinonimos[palabra]
                palabras_expandidas.append(palabra_principal)
                expansiones_realizadas.append(f"{palabra} → {palabra_principal}")
            else:
                palabras_expandidas.append(palabra)
        
        resultado = ' '.join(palabras_expandidas)
        
        if expansiones_realizadas:
            print(f"   🔤 Expansiones: {', '.join(expansiones_realizadas)}")
        
        return resultado


    def corregir_errores_tipograficos(self, texto):
        """
        Método para agregar a la clase SistemaNormalizacion
        AGREGAR ESTE MÉTODO A TU CLASE EXISTENTE
        """
        
        if not hasattr(self, 'correcciones'):
            return texto
        
        texto_corregido = texto
        correcciones_realizadas = []
        
        # Aplicar correcciones solo en contexto de palabras
        for incorrecto, correcto in self.correcciones.items():
            # Buscar el carácter incorrecto dentro de palabras
            patron = rf'\b\w*{re.escape(incorrecto)}\w*\b'
            coincidencias = re.findall(patron, texto_corregido)
            
            for coincidencia in coincidencias:
                if incorrecto in coincidencia:
                    corregida = coincidencia.replace(incorrecto, correcto)
                    texto_corregido = texto_corregido.replace(coincidencia, corregida)
                    correcciones_realizadas.append(f"{coincidencia} → {corregida}")
        
        if correcciones_realizadas:
            print(f"   ✏️ Correcciones: {', '.join(correcciones_realizadas)}")
        
        return texto_corregido

    def limpieza_especifica_por_tipo(self, texto, tipo_catalogo):
        """
        Limpieza específica según el tipo de catálogo
        AGREGAR ESTE MÉTODO NUEVO A LA CLASE
        """
        
        if not tipo_catalogo:
            return texto
        
        texto_especifico = texto
        
        if tipo_catalogo == 'ESTADOS':
            # Estados: más estricto, nombres generalmente fijos
            # Remover palabras innecesarias comunes
            palabras_innecesarias = ['ESTADO', 'DE', 'EL', 'LA', 'LOS', 'LAS']
            palabras = texto_especifico.split()
            palabras_filtradas = [p for p in palabras if p not in palabras_innecesarias or len(palabras) <= 2]
            texto_especifico = ' '.join(palabras_filtradas)
            
        elif tipo_catalogo == 'CIUDADES':
            # Ciudades: normalizar prefijos comunes
            if texto_especifico.startswith('CIUDAD '):
                texto_especifico = texto_especifico  # Mantener CIUDAD
            elif texto_especifico.startswith('CD '):
                texto_especifico = 'CIUDAD ' + texto_especifico[3:]
                
        elif tipo_catalogo == 'MUNICIPIOS':
            # Municipios: similar a ciudades pero más flexible
            if texto_especifico.startswith('MUNICIPIO '):
                texto_especifico = texto_especifico[10:]  # Remover prefijo
            elif texto_especifico.startswith('MPIO '):
                texto_especifico = texto_especifico[5:]  # Remover prefijo
                
        elif tipo_catalogo == 'ALCALDIAS':
            # Alcaldías: nombres generalmente fijos de CDMX
            pass  # Sin cambios específicos
            
        elif tipo_catalogo == 'COLONIAS':
            # Colonias: la más flexible, muchas variaciones
            # Remover prefijos comunes de colonias
            prefijos_colonia = ['COLONIA ', 'COL ', 'BARRIO ', 'FRACCIONAMIENTO ', 'FRACC ']
            for prefijo in prefijos_colonia:
                if texto_especifico.startswith(prefijo):
                    texto_especifico = texto_especifico[len(prefijo):]
                    break
        
        if texto_especifico != texto:
            print(f"   Específico {tipo_catalogo}: '{texto}' → '{texto_especifico}'")
        
        return texto_especifico

       


    # ========================================
    # MÉTODO PARA AGREGAR A LA CLASE
    # ========================================

    def inicializar_patrones_limpieza(self):
        """
        Inicializar patrones de limpieza
        AGREGAR ESTE MÉTODO A LA CLASE
        """
        
        # Cargar patrones globales en la instancia
        self.patrones_limpieza = PATRONES_LIMPIEZA_MEXICO.copy()
        
        print(f"   ✅ {len(self.patrones_limpieza)} patrones de limpieza cargados")
        
        # Compilar expresiones regulares para mejor rendimiento
        self.patrones_compilados = []
        for patron, reemplazo in self.patrones_limpieza:
            try:
                regex_compilado = re.compile(patron)
                self.patrones_compilados.append((regex_compilado, reemplazo))
            except re.error as e:
                print(f"   ⚠️ Error compilando patrón '{patron}': {e}")
        










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

    
    def normalizar_registro(self, texto_original, tipo_catalogo, division, campo_status, campo_clave, campo_descripcion):
        """Normalizar un registro individual usando los algoritmos de IA"""
        
        # Limpiar texto
        texto_limpio = self.limpiar_texto_inteligente(texto_original)
        
        # Buscar en referencias
        referencia_encontrada = self.buscar_en_referencias_CORREGIDO(texto_limpio, tipo_catalogo)
        
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
    
    def limpiar_texto(self, texto, tipo_catalogo=None):
        """
        Limpieza inteligente que reemplaza al método limpiar_texto() original
        REEMPLAZAR EL MÉTODO EXISTENTE limpiar_texto() POR ESTE
        """
        
        if not isinstance(texto, str):
            return ""
        
        print(f"🧠 Limpieza inteligente: '{texto}' (tipo: {tipo_catalogo})")
        
        # PASO 1: Conversión básica
        texto_procesado = texto.upper().strip()
        print(f"   Mayúsculas: '{texto_procesado}'")
        
        # PASO 2: Expandir abreviaciones ANTES de limpiar (usa diccionarios Paso 1)
        if hasattr(self, 'expandir_abreviaciones_inteligente'):
            texto_expandido = self.expandir_abreviaciones_inteligente(texto_procesado)
            if texto_expandido != texto_procesado:
                print(f"   Expandido: '{texto_expandido}'")
                texto_procesado = texto_expandido
        
        # PASO 3: Correcciones tipográficas ANTES de limpiar (usa diccionarios Paso 1)
        if hasattr(self, 'corregir_errores_tipograficos'):
            texto_corregido = self.corregir_errores_tipograficos(texto_procesado)
            if texto_corregido != texto_procesado:
                print(f"   Corregido: '{texto_corregido}'")
                texto_procesado = texto_corregido
        
        # PASO 4: Aplicar patrones específicos de limpieza
        for patron, reemplazo in PATRONES_LIMPIEZA_MEXICO:
            texto_anterior = texto_procesado
            texto_procesado = re.sub(patron, reemplazo, texto_procesado)
            if texto_procesado != texto_anterior:
                print(f"   Patrón aplicado: '{texto_anterior}' → '{texto_procesado}'")
        
        # PASO 5: Quitar acentos (proceso original)
        texto_sin_acentos = unicodedata.normalize('NFD', texto_procesado)
        texto_sin_acentos = ''.join(char for char in texto_sin_acentos if unicodedata.category(char) != 'Mn')
        
        # PASO 6: Limpiar caracteres especiales (proceso original)  
        texto_limpio = re.sub(r'[^\w\s]', ' ', texto_sin_acentos)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        
        # PASO 7: Limpieza final específica por tipo de catálogo
        texto_final = self.limpieza_especifica_por_tipo(texto_limpio, tipo_catalogo)
        
        print(f"   Resultado final: '{texto_final}'")
        return texto_final
    
    
    
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
    """
    Versión más simple que solo oculta el botón después de cualquier carga exitosa
    ALTERNATIVA si la versión de arriba es muy compleja
    """
    
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
            
            st.markdown("**Vista previa del archivo:**")
            st.dataframe(df_ref.head(), use_container_width=True)
            
            # Información del archivo
            st.info(f"""
            **Información del archivo:**
            - Registros: {len(df_ref):,}
            - Columnas: {list(df_ref.columns)}
            - Tipo seleccionado: {tipo_ref}
            """)
            
            # Validaciones básicas
            columnas_requeridas = ['codigo_oficial', 'nombre_oficial']
            columnas_faltantes = set(columnas_requeridas) - set(df_ref.columns)
            
            if columnas_faltantes:
                st.error(f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}")
            else:
                # ===== CONTROL SIMPLE DE BOTÓN =====
                
                # Verificar si ya hubo una carga exitosa en esta sesión
                if not st.session_state.get('carga_exitosa_reciente', False):
                    
                    # MOSTRAR BOTÓN
                    if st.button("🚀 CARGAR CON ACTUALIZACIÓN AUTOMÁTICA", type="primary"):
                        
                        st.write("🔄 INICIANDO CARGA...")
                        
                        # Ejecutar la carga
                        success = cargar_referencias_con_actualizacion_automatica(
                            df_ref, tipo_ref, fuente_ref, archivo_referencia.name
                        )
                        
                        if success:
                            # MARCAR COMO EXITOSA
                            st.session_state['carga_exitosa_reciente'] = True
                            st.success("✅ CARGA COMPLETADA - ACTUALIZANDO VISTA...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Error en la carga")
                
                else:
                    # MOSTRAR MENSAJE EN LUGAR DEL BOTÓN
                    st.success("""
                    ✅ **CARGA COMPLETADA EXITOSAMENTE**
                    
                    El archivo ha sido procesado y las referencias están actualizadas.
                    """)
                    
                    # Botón para reiniciar (opcional)
                    if st.button("🔄 Cargar Otro Archivo"):
                        st.session_state['carga_exitosa_reciente'] = False
                        st.rerun()
        
        except Exception as e:
            st.error(f"Error leyendo archivo de referencia: {str(e)}")

    

def mostrar_referencias_actuales():
    """
    Mostrar las referencias actuales en el sistema - VERSIÓN MEJORADA
    REEMPLAZAR la función mostrar_referencias_actuales() existente por esta
    """
    
    sistema = SistemaNormalizacion()
    
    # Crear un container que se pueda actualizar
    referencias_container = st.container()
    
    with referencias_container:
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
                
                # Formatear fecha para mejor legibilidad
                df_referencias['Última Actualización'] = pd.to_datetime(
                    df_referencias['Última Actualización']
                ).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                st.dataframe(df_referencias, use_container_width=True, hide_index=True)
                
                # Mostrar estadísticas adicionales
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_global = df_referencias['Total Referencias'].sum()
                    st.metric("Total Global", f"{total_global:,}")
                
                with col2:
                    tipos_disponibles = len(df_referencias)
                    st.metric("Tipos de Catálogo", tipos_disponibles)
                
                with col3:
                    # Fecha más reciente
                    fecha_mas_reciente = pd.to_datetime(
                        df_referencias['Última Actualización']
                    ).max().strftime('%Y-%m-%d')
                    st.metric("Última Carga", fecha_mas_reciente)
                
            else:
                st.info("📝 No hay referencias cargadas en el sistema. Sube archivos de referencia SEPOMEX/INEGI para mejorar la precisión.")
        
        except Exception as e:
            st.error(f"Error consultando referencias: {str(e)}")

# ========================================
# CORRECCIÓN PARA ERROR EN PROCESAMIENTO TIEMPO REAL
# ========================================

def mostrar_procesamiento_tiempo_real():
    """Mostrar el progreso de procesamiento en tiempo real - SIN BOTÓN ELIMINAR"""
    
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
                    
                    # BOTONES AJUSTADOS - SIN ELIMINAR (2 columnas en lugar de 3)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"📊 Ver Resultados", key=f"ver_{archivo['id_archivo']}", use_container_width=True):
                            mostrar_resultados_archivo(archivo['id_archivo'])
                    
                    with col2:
                        if st.button(f"📥 Descargar", key=f"desc_{archivo['id_archivo']}", use_container_width=True):
                            descargar_resultados_archivo(archivo['id_archivo'])
                    
                    # INFORMACIÓN ADICIONAL EN LUGAR DEL BOTÓN ELIMINAR
                    if archivo['estado_procesamiento'] == 'COMPLETADO':
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Calcular tasa de éxito
                            if procesados > 0:
                                # Obtener estadísticas del archivo
                                try:
                                    with sistema.engine.connect() as conn_stats:
                                        result_stats = conn_stats.execute(text("""
                                            SELECT 
                                                COUNT(CASE WHEN valor_normalizado IS NOT NULL THEN 1 END) as exitosos,
                                                COALESCE(AVG(CASE WHEN confianza > 0 THEN confianza END), 0) as confianza_prom
                                            FROM resultados_normalizacion 
                                            WHERE id_archivo = :id_archivo
                                        """), {'id_archivo': archivo['id_archivo']})
                                        
                                        stats_row = result_stats.fetchone()
                                        if stats_row:
                                            exitosos = int(stats_row[0] or 0)
                                            confianza_prom = float(stats_row[1] or 0)
                                            tasa_exito = (exitosos / procesados * 100) if procesados > 0 else 0
                                            
                                            st.success(f"✅ **Éxito:** {tasa_exito:.1f}% ({exitosos:,}/{procesados:,})")
                                        else:
                                            st.info("ℹ️ **Estado:** Completado")
                                except:
                                    st.info("ℹ️ **Estado:** Completado")
                            else:
                                st.info("ℹ️ **Estado:** Completado")
                        
                        with col2:
                            # Mostrar confianza promedio si está disponible
                            try:
                                with sistema.engine.connect() as conn_conf:
                                    result_conf = conn_conf.execute(text("""
                                        SELECT COALESCE(AVG(CASE WHEN confianza > 0 THEN confianza END), 0) as confianza_prom
                                        FROM resultados_normalizacion 
                                        WHERE id_archivo = :id_archivo
                                    """), {'id_archivo': archivo['id_archivo']})
                                    
                                    conf_row = result_conf.fetchone()
                                    if conf_row and conf_row[0] > 0:
                                        confianza = float(conf_row[0]) * 100
                                        st.info(f"🎯 **Confianza:** {confianza:.1f}%")
                                    else:
                                        fecha_formato = pd.to_datetime(archivo['fecha_carga']).strftime('%d/%m/%Y %H:%M')
                                        st.info(f"📅 **Procesado:** {fecha_formato}")
                            except:
                                fecha_formato = pd.to_datetime(archivo['fecha_carga']).strftime('%d/%m/%Y %H:%M')
                                st.info(f"📅 **Procesado:** {fecha_formato}")
                    
                    else:
                        # Para archivos en proceso
                        st.info(f"⏳ **Estado:** {archivo['estado_procesamiento']}")
        
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



def mostrar_resultados_archivo(id_archivo):
    """Mostrar resultados detallados de un archivo procesado - RESPONSIVO"""
    
    sistema = SistemaNormalizacion()
    
    try:
        with sistema.engine.connect() as conn:
            # Obtener información del archivo
            result = conn.execute(text("""
                SELECT * FROM archivos_cargados WHERE id_archivo = :id_archivo
            """), {'id_archivo': id_archivo})
            
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
            
            # Tabla de resultados RESPONSIVA
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
                'texto_original': 'Original',
                'valor_normalizado': 'Normalizado',
                'metodo_usado': 'Método',
                'confianza': 'Confianza',
                'requiere_revision': 'Revisión',
                'fecha_proceso': 'Fecha'
            })
            
            # CONFIGURACIÓN RESPONSIVA AVANZADA
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True, 
                height=400,
                column_config={
                    "Original": st.column_config.TextColumn(
                        "Original",
                        help="Texto original de AS400",
                        width="medium",
                        max_chars=50
                    ),
                    "Normalizado": st.column_config.TextColumn(
                        "Normalizado", 
                        help="Texto normalizado con SEPOMEX",
                        width="medium",
                        max_chars=50
                    ),
                    "Método": st.column_config.TextColumn(
                        "Método",
                        help="Algoritmo usado para normalización",
                        width="small"
                    ),
                    "Confianza": st.column_config.TextColumn(
                        "Confianza",
                        help="Nivel de confianza del resultado",
                        width="small"
                    ),
                    "Revisión": st.column_config.TextColumn(
                        "Revisión",
                        help="Indica si requiere validación manual",
                        width="small"
                    ),
                    "Fecha": st.column_config.TextColumn(
                        "Fecha",
                        help="Fecha y hora de procesamiento",
                        width="small"
                    )
                }
            )
            
            # VISTA MÓVIL ALTERNATIVA
            if st.checkbox("📱 Vista Móvil Compacta", help="Activa para pantallas pequeñas"):
                st.markdown("### 📋 Vista Compacta")
                
                # Mostrar solo datos esenciales en formato de cards
                for idx, row in df_display.head(10).iterrows():  # Solo primeros 10 en vista móvil
                    with st.expander(f"📄 {row['Original'][:30]}..."):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Original:** {row['Original']}")
                            st.write(f"**Método:** {row['Método']}")
                            st.write(f"**Fecha:** {row['Fecha']}")
                        
                        with col2:
                            st.write(f"**Normalizado:** {row['Normalizado']}")
                            st.write(f"**Confianza:** {row['Confianza']}")
                            st.write(f"**Revisión:** {row['Revisión']}")
            
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
    
    usuario_actual = st.session_state.get('usuario_actual', {})
    rol_usuario = usuario_actual.get('rol', 'USUARIO')
    
    # Tabs diferentes según el rol
    if rol_usuario == 'SUPERUSUARIO':
        # SUPERUSUARIO: Ve todo
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗄️ Base de Datos", 
            "📚 Referencias", 
            "🧹 Mantenimiento", 
            "📊 Estadísticas"
        ])
        
        with tab1:
            mostrar_config_base_datos()  # Con parámetros del sistema
        
        with tab2:
            mostrar_gestion_referencias()
        
        with tab3:
            mostrar_mantenimiento_sistema()
        
        with tab4:
            mostrar_estadisticas_sistema()
    
    elif rol_usuario == 'GERENTE':
        # GERENTE: Sin parámetros técnicos
        tab1, tab2, tab3 = st.tabs([
            "🗄️ Base de Datos", 
            "📚 Referencias", 
            "📊 Estadísticas"
        ])
        
        with tab1:
            mostrar_config_base_datos()  # Sin parámetros del sistema
        
        with tab2:
            mostrar_gestion_referencias()
        
        with tab3:
            mostrar_estadisticas_sistema()
    
    else:
        # USUARIO: Acceso muy limitado
        st.error("❌ No tienes permisos para acceder a la configuración del sistema")
        st.info("""
        👤 **Acceso de Usuario:**
        
        La configuración del sistema está restringida a administradores.
        
        📞 **¿Necesitas cambiar algo?** Contacta a un gerente o administrador.
        """)
# ========================================
# CORRECCIÓN ADICIONAL PARA OTRAS FUNCIONES SIMILARES
# ========================================

def mostrar_config_base_datos():
    """Configuración de base de datos - CORREGIDA"""
    
    st.markdown("### 🗄️ Configuración de PostgreSQL")
    
    sistema = SistemaNormalizacion()
    usuario_actual = st.session_state.get('usuario_actual', {})
    rol_usuario = usuario_actual.get('rol', 'USUARIO')
    
    # Estado de conexión (todos pueden ver esto)
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
                        relname as tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                    ORDER BY relname
                """))

                # CORRECCIÓN: Manejar resultados correctamente
                tablas_stats = []
                for row in result:
                    if row is not None:
                        tablas_stats.append(dict(row._mapping))
            
            # Mostrar información básica (todos pueden ver)
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
    
    st.markdown("---")
    
    # CONTROL DE ACCESO: Solo SUPERUSUARIOS ven parámetros del sistema
    if rol_usuario == 'SUPERUSUARIO':
        mostrar_parametros_sistema_admin()
    else:
        mostrar_mensaje_permisos_parametros(rol_usuario)

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

#def main():
def main_aplicacion_original():
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
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        try:
            st.image("logo_RN.png", width=120)
        except:
            st.markdown("🏠")
    with col_title:
        st.markdown("""
        <div  style="text-align: left;">
            <h3>Red Nacional Última Milla</h3>
            <h5>Sistema Integral de Normalización Domicilios | Procesamiento Inteligente de Domicilios</h5>
        </div>
        """, unsafe_allow_html=True)
    
    # NAVEGACIÓN PRINCIPAL CON CONTROL POR ROL
    # Obtener rol del usuario actual
    usuario_actual = st.session_state.get('usuario_actual', {})
    rol_usuario = usuario_actual.get('rol', 'USUARIO')
    
    # Definir pestañas según el rol
    if rol_usuario in ['SUPERUSUARIO', 'GERENTE']:
        # ADMINISTRADORES: Ven todas las pestañas
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
    
    else:
        # USUARIOS NORMALES: Solo ven 3 pestañas
        tab1, tab2, tab3 = st.tabs([
            "📊 Dashboard", 
            "📁 Carga de Archivos", 
            "📋 Resultados"
        ])
        
        with tab1:
            mostrar_dashboard_principal()
        
        with tab2:
            # Los usuarios pueden ver la interfaz pero con funciones limitadas
            mostrar_interfaz_carga_limitada()
        
        with tab3:
            mostrar_seccion_resultados()

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
    """Generar descarga de resultados de un archivo - CORREGIDO"""

    sistema = SistemaNormalizacion()

    try:
        with sistema.engine.connect() as conn:
            # Obtener información del archivo
            result = conn.execute(text("""
                SELECT nombre_archivo, tipo_catalogo, division 
                FROM archivos_cargados WHERE id_archivo = :id_archivo
            """), {'id_archivo': id_archivo})
            
            # CORRECCIÓN: Manejar correctamente el resultado
            archivo_row = result.fetchone()
            if archivo_row is None:
                st.error("❌ No se encontró el archivo especificado.")
                return
                
            archivo_info = dict(archivo_row._mapping)
            
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
            
            # CORRECCIÓN: Convertir correctamente a lista de diccionarios
            resultados = []
            for row in result:
                if row is not None:
                    resultados.append(dict(row._mapping))
        
        if not resultados:
            st.warning("No hay resultados para descargar")
            return
        
        # Crear DataFrames para diferentes formatos
        df_completo = pd.DataFrame(resultados)
        
        # Verificar que las columnas existan antes de usarlas
        columnas_as400 = ['campo_status', 'campo_clave', 'valor_normalizado', 'codigo_normalizado']
        columnas_disponibles = [col for col in columnas_as400 if col in df_completo.columns]
        
        if not columnas_disponibles:
            st.error("❌ No se encontraron las columnas necesarias para generar el archivo AS400")
            return
        
        # Formato para AS400 (solo campos disponibles)
        df_as400 = df_completo[columnas_disponibles].copy()
        
        # Renombrar columnas para AS400
        nombres_as400 = {
            'campo_status': 'STATUS',
            'campo_clave': 'CLAVE_ORIGINAL', 
            'valor_normalizado': 'DESCRIPCION_NORMALIZADA',
            'codigo_normalizado': 'CODIGO_NORMALIZADO'
        }
        
        df_as400 = df_as400.rename(columns={k: v for k, v in nombres_as400.items() if k in df_as400.columns})
        
        # Formato para revisión manual (solo casos que requieren revisión)
        if 'requiere_revision' in df_completo.columns:
            df_revision = df_completo[df_completo['requiere_revision'] == True].copy()
        else:
            df_revision = pd.DataFrame()  # DataFrame vacío si no existe la columna
        
        # Crear archivo ZIP con múltiples formatos
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            # Archivo completo
            csv_completo = df_completo.to_csv(index=False)
            zip_file.writestr(f"{archivo_info['nombre_archivo']}_completo.csv", csv_completo)
            
            # Archivo para AS400
            csv_as400 = df_as400.to_csv(index=False)
            zip_file.writestr(f"{archivo_info['nombre_archivo']}_as400.csv", csv_as400)
            
            # Archivo de casos para revisión (solo si hay datos)
            if not df_revision.empty:
                csv_revision = df_revision.to_csv(index=False)
                zip_file.writestr(f"{archivo_info['nombre_archivo']}_revision.csv", csv_revision)
            
            # Reporte de resumen
            total_registros = len(resultados)
            registros_exitosos = len(df_completo[df_completo['valor_normalizado'].notna()]) if 'valor_normalizado' in df_completo.columns else 0
            requieren_revision = len(df_revision)
            
            # Calcular confianza promedio de manera segura
            if 'confianza' in df_completo.columns:
                confianzas_validas = df_completo['confianza'].dropna()
                confianza_promedio = confianzas_validas.mean() if len(confianzas_validas) > 0 else 0
            else:
                confianza_promedio = 0
            
            # Distribución de métodos de manera segura
            if 'metodo_usado' in df_completo.columns:
                distribucion_metodos = df_completo['metodo_usado'].value_counts().to_string()
            else:
                distribucion_metodos = "No disponible"
            
            resumen = f"""
REPORTE DE PROCESAMIENTO
========================

Archivo: {archivo_info['nombre_archivo']}
Tipo: {archivo_info.get('tipo_catalogo', 'N/A')}
División: {archivo_info.get('division', 'N/A')}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ESTADÍSTICAS:
- Total de registros: {total_registros:,}
- Registros exitosos: {registros_exitosos:,}
- Requieren revisión: {requieren_revision:,}
- Confianza promedio: {confianza_promedio:.1%}

MÉTODOS UTILIZADOS:
{distribucion_metodos}

ARCHIVOS INCLUIDOS:
- {archivo_info['nombre_archivo']}_completo.csv: Todos los resultados
- {archivo_info['nombre_archivo']}_as400.csv: Formato para cargar en AS400
""" + (f"- {archivo_info['nombre_archivo']}_revision.csv: Casos que requieren revisión manual\n" if not df_revision.empty else "")
            
            zip_file.writestr(f"{archivo_info['nombre_archivo']}_reporte.txt", resumen)
        
        # Preparar descarga
        zip_buffer.seek(0)
        
        nombre_descarga = f"resultados_{archivo_info.get('tipo_catalogo', 'datos')}_{archivo_info.get('division', 'general')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        st.download_button(
            label="📥 Descargar Resultados Completos",
            data=zip_buffer.getvalue(),
            file_name=nombre_descarga,
            mime="application/zip"
        )
        
        st.success(f"✅ Preparado para descarga: {len(resultados):,} registros")
        
    except Exception as e:
        st.error(f"Error preparando descarga: {str(e)}")
        # Debug adicional
        st.code(f"""
Detalles del error:
- Función: descargar_resultados_archivo()
- ID Archivo: {id_archivo}
- Error específico: {str(e)}
- Tipo de error: {type(e).__name__}
        """)

def eliminar_archivo_procesado(id_archivo):
    """Eliminar archivo procesado y sus resultados - FUNCIÓN CORREGIDA"""
    
    # ⚠️ IMPORTANTE: Usar st.session_state para evitar recrear el sistema
    if 'sistema_normalizacion' not in st.session_state:
        st.session_state.sistema_normalizacion = SistemaNormalizacion()
    
    sistema = st.session_state.sistema_normalizacion
    
    # Crear un único checkbox por archivo
    checkbox_key = f"confirm_delete_{id_archivo}"
    
    if st.checkbox("⚠️ Confirmar eliminación (esta acción no se puede deshacer)", key=checkbox_key):
        try:
            with sistema.engine.connect() as conn:
                # Primero obtener información del archivo para mostrarla
                result = conn.execute(text("""
                    SELECT nombre_archivo, tipo_catalogo, division 
                    FROM archivos_cargados 
                    WHERE id_archivo = :id_archivo
                """), {'id_archivo': id_archivo})
                
                archivo_info = result.fetchone()
                if not archivo_info:
                    st.error("❌ Archivo no encontrado")
                    return
                
                archivo_data = dict(archivo_info._mapping)
                
                # Contar registros que se van a eliminar
                result = conn.execute(text("""
                    SELECT COUNT(*) as total_resultados
                    FROM resultados_normalizacion 
                    WHERE id_archivo = :id_archivo
                """), {'id_archivo': id_archivo})
                
                total_resultados = result.fetchone()[0]
                
                # Mostrar información de lo que se va a eliminar
                st.warning(f"""
                **Se eliminará:**
                - 📄 Archivo: {archivo_data['nombre_archivo']}
                - 📋 Tipo: {archivo_data['tipo_catalogo']}
                - 🏢 División: {archivo_data['division']}
                - 📊 Resultados: {total_resultados:,} registros
                """)
                
                # Botón final de confirmación
                if st.button(f"🗑️ ELIMINAR DEFINITIVAMENTE", key=f"final_delete_{id_archivo}", type="primary"):
                    
                    # Eliminar resultados primero (por clave foránea)
                    result_delete = conn.execute(text("""
                        DELETE FROM resultados_normalizacion 
                        WHERE id_archivo = :id_archivo
                    """), {'id_archivo': id_archivo})
                    
                    resultados_eliminados = result_delete.rowcount
                    
                    # Eliminar registro del archivo
                    archivo_delete = conn.execute(text("""
                        DELETE FROM archivos_cargados 
                        WHERE id_archivo = :id_archivo
                    """), {'id_archivo': id_archivo})
                    
                    archivos_eliminados = archivo_delete.rowcount
                    
                    # Confirmar transacción
                    conn.commit()
                    
                    # Mostrar resultado
                    if archivos_eliminados > 0:
                        st.success(f"""
                        ✅ **Eliminación completada:**
                        - 📄 Archivo eliminado: {archivo_data['nombre_archivo']}
                        - 📊 Resultados eliminados: {resultados_eliminados:,}
                        - 🔄 Recarga la página para ver los cambios
                        """)
                        
                        # Forzar recarga después de 2 segundos
                        st.rerun()
                        
                    else:
                        st.error("❌ No se pudo eliminar el archivo")
        
        except Exception as e:
            st.error(f"❌ Error eliminando archivo: {str(e)}")
            
            # Mostrar detalles técnicos para debug
            with st.expander("🔧 Detalles técnicos del error"):
                st.code(f"""
Error específico: {str(e)}
Tipo de error: {type(e).__name__}
ID Archivo: {id_archivo}
                """)
    else:
        st.info("👆 Marca la casilla de confirmación para continuar con la eliminación")







# ========================================
# HERRAMIENTAS DE DIAGNÓSTICO PARA ELIMINACIÓN
# ========================================

# ========================================
# DIAGNÓSTICO AVANZADO DE BASE DE DATOS
# ========================================

def diagnostico_completo_bd():
    """
    Diagnóstico completo para identificar problemas de BD
    """
    
    st.markdown("## 🔬 Diagnóstico Avanzado de Base de Datos")
    
    if 'sistema_global' not in st.session_state:
        st.session_state.sistema_global = SistemaNormalizacion()
    
    sistema = st.session_state.sistema_global
    
    # Test 1: Verificar conexión básica
    st.markdown("### 1️⃣ Test de Conexión Básica")
    
    try:
        with sistema.engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_result = result.fetchone()[0]
            
            if test_result == 1:
                st.success("✅ Conexión a PostgreSQL OK")
            else:
                st.error("❌ Problema en conexión básica")
                
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return
    
    # Test 2: Verificar permisos de escritura
    st.markdown("### 2️⃣ Test de Permisos de Escritura")
    
    try:
        with sistema.engine.connect() as conn:
            # Intentar crear una tabla temporal
            conn.execute(text("""
                CREATE TEMPORARY TABLE test_permisos (
                    id INTEGER,
                    test_text VARCHAR(50)
                )
            """))
            
            # Intentar insertar datos
            conn.execute(text("""
                INSERT INTO test_permisos (id, test_text) VALUES (1, 'test')
            """))
            
            # Intentar hacer commit
            conn.commit()
            
            # Verificar que se insertó
            result = conn.execute(text("SELECT COUNT(*) FROM test_permisos"))
            count = result.fetchone()[0]
            
            if count == 1:
                st.success("✅ Permisos de escritura OK")
            else:
                st.error("❌ Problema con permisos de escritura")
                
    except Exception as e:
        st.error(f"❌ Error de permisos: {str(e)}")
        st.code(f"Error específico: {str(e)}")
    
    # Test 3: Verificar estructura de tablas
    st.markdown("### 3️⃣ Test de Estructura de Tablas")
    
    try:
        with sistema.engine.connect() as conn:
            # Verificar que las tablas existen
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('archivos_cargados', 'resultados_normalizacion')
                ORDER BY table_name
            """))
            
            tablas = [row[0] for row in result]
            
            st.write("**Tablas encontradas:**")
            for tabla in tablas:
                st.success(f"✅ {tabla}")
            
            if 'archivos_cargados' not in tablas:
                st.error("❌ Falta tabla 'archivos_cargados'")
            if 'resultados_normalizacion' not in tablas:
                st.error("❌ Falta tabla 'resultados_normalizacion'")
                
    except Exception as e:
        st.error(f"❌ Error verificando tablas: {str(e)}")
    
    # Test 4: Test de DELETE directo
    st.markdown("### 4️⃣ Test de DELETE Directo")
    
    if st.button("🧪 Probar DELETE Directo"):
        try:
            with sistema.engine.connect() as conn:
                
                # Primero crear un registro de prueba
                st.info("Creando registro de prueba...")
                
                test_id = f"test-{int(time.time())}"
                
                conn.execute(text("""
                    INSERT INTO archivos_cargados 
                    (id_archivo, nombre_archivo, tipo_catalogo, division, total_registros)
                    VALUES (:id, 'test_file.csv', 'ESTADOS', 'TEST', 10)
                """), {'id': test_id})
                
                conn.commit()
                st.success("✅ Registro de prueba creado")
                
                # Verificar que se creó
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM archivos_cargados WHERE id_archivo = :id
                """), {'id': test_id})
                
                count_antes = result.fetchone()[0]
                st.write(f"Registros antes del DELETE: {count_antes}")
                
                # Intentar eliminarlo
                st.info("Intentando DELETE...")
                
                delete_result = conn.execute(text("""
                    DELETE FROM archivos_cargados WHERE id_archivo = :id
                """), {'id': test_id})
                
                registros_eliminados = delete_result.rowcount
                st.write(f"Registros que reporta haber eliminado: {registros_eliminados}")
                
                # CRÍTICO: Hacer commit
                conn.commit()
                st.info("✅ COMMIT ejecutado")
                
                # Verificar que se eliminó
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM archivos_cargados WHERE id_archivo = :id
                """), {'id': test_id})
                
                count_despues = result.fetchone()[0]
                st.write(f"Registros después del DELETE: {count_despues}")
                
                if count_despues == 0:
                    st.success("🎉 **DELETE FUNCIONA CORRECTAMENTE**")
                    st.success("El problema NO es la función DELETE")
                else:
                    st.error("❌ **DELETE NO FUNCIONA**")
                    st.error("Hay un problema fundamental con los permisos o la BD")
                    
        except Exception as e:
            st.error(f"❌ Error en test DELETE: {str(e)}")
            st.code(f"""
ERROR COMPLETO:
{str(e)}

Tipo: {type(e).__name__}
""")
    
    # Test 5: Información de la sesión de BD
    st.markdown("### 5️⃣ Información de Sesión de BD")
    
    try:
        with sistema.engine.connect() as conn:
            # Usuario actual
            result = conn.execute(text("SELECT current_user"))
            usuario = result.fetchone()[0]
            st.info(f"**Usuario conectado:** {usuario}")
            
            # Base de datos actual
            result = conn.execute(text("SELECT current_database()"))
            database = result.fetchone()[0]
            st.info(f"**Base de datos:** {database}")
            
            # Configuración de autocommit
            result = conn.execute(text("SHOW autocommit"))
            autocommit = result.fetchone()[0]
            st.info(f"**Autocommit:** {autocommit}")
            
            # Transacciones activas
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pg_stat_activity 
                WHERE datname = current_database() AND state = 'active'
            """))
            transacciones = result.fetchone()[0]
            st.info(f"**Transacciones activas:** {transacciones}")
            
    except Exception as e:
        st.error(f"❌ Error obteniendo info de sesión: {str(e)}")


def eliminar_archivo_ultra_simple(id_archivo):
    """
    Eliminación ultra simple usando psycopg2 directo
    REEMPLAZAR LA FUNCIÓN PROBLEMÁTICA POR ESTA
    """
    
    st.markdown("### 🗑️ Eliminación Ultra Simple")
    
    # Confirmación
    if st.checkbox("⚠️ Confirmar eliminación definitiva", key=f"confirm_ultra_{id_archivo}"):
        
        if st.button("🗑️ ELIMINAR CON PSYCOPG2", key=f"ultra_delete_{id_archivo}", type="primary"):
            
            try:
                import psycopg2
                
                # Progreso
                progress = st.progress(0)
                status = st.empty()
                
                # Conectar con psycopg2 directo
                status.text("🔌 Conectando con psycopg2...")
                progress.progress(0.1)
                
                conn = psycopg2.connect(
                    host=DATABASE_CONFIG['host'],
                    port=DATABASE_CONFIG['port'],
                    database=DATABASE_CONFIG['database'],
                    user=DATABASE_CONFIG['user'],
                    password=DATABASE_CONFIG['password']
                )
                
                cursor = conn.cursor()
                
                # Obtener info del archivo
                status.text("📋 Obteniendo información del archivo...")
                progress.progress(0.2)
                
                cursor.execute("""
                    SELECT nombre_archivo, tipo_catalogo, division 
                    FROM archivos_cargados WHERE id_archivo = %s
                """, (id_archivo,))
                
                archivo_info = cursor.fetchone()
                
                if not archivo_info:
                    st.error("❌ Archivo no encontrado")
                    conn.close()
                    return
                
                nombre, tipo, division = archivo_info
                
                # Contar registros a eliminar
                status.text("🔢 Contando registros...")
                progress.progress(0.3)
                
                cursor.execute("SELECT COUNT(*) FROM resultados_normalizacion WHERE id_archivo = %s", (id_archivo,))
                total_resultados = cursor.fetchone()[0]
                
                # ELIMINAR RESULTADOS
                status.text(f"🗑️ Eliminando {total_resultados} resultados...")
                progress.progress(0.5)
                
                cursor.execute("DELETE FROM resultados_normalizacion WHERE id_archivo = %s", (id_archivo,))
                resultados_eliminados = cursor.rowcount
                
                # ELIMINAR ARCHIVO
                status.text("🗑️ Eliminando registro del archivo...")
                progress.progress(0.7)
                
                cursor.execute("DELETE FROM archivos_cargados WHERE id_archivo = %s", (id_archivo,))
                archivos_eliminados = cursor.rowcount
                
                # COMMIT EXPLÍCITO
                status.text("💾 Guardando cambios...")
                progress.progress(0.9)
                
                conn.commit()
                
                # VERIFICAR
                cursor.execute("SELECT COUNT(*) FROM archivos_cargados WHERE id_archivo = %s", (id_archivo,))
                verificacion = cursor.fetchone()[0]
                
                progress.progress(1.0)
                
                if verificacion == 0:
                    status.text("✅ Eliminación completada!")
                    
                    st.success(f"""
                    ### ✅ ELIMINACIÓN EXITOSA
                    
                    **Archivo eliminado:** {nombre}
                    **Tipo:** {tipo} | **División:** {division}
                    **Resultados eliminados:** {resultados_eliminados:,}
                    **Registros de archivo:** {archivos_eliminados}
                    
                    🔄 **Recargando página...**
                    """)
                    
                    # Auto-reload
                    time.sleep(2)
                    st.rerun()
                    
                else:
                    st.error("❌ La eliminación no se completó correctamente")
                
                conn.close()
                
            except Exception as e:
                st.error(f"❌ Error en eliminación ultra simple: {str(e)}")
                st.code(f"""
ERROR COMPLETO:
{str(e)}

ID Archivo: {id_archivo}
Función: eliminar_archivo_ultra_simple()
                """)




# ========================================
# FUNCIÓN AUXILIAR: INTERFAZ LIMITADA PARA USUARIOS
# ========================================

def mostrar_interfaz_carga_limitada():
    """Interfaz de carga limitada para usuarios normales"""
    
    usuario_actual = st.session_state.get('usuario_actual', {})
    rol_usuario = usuario_actual.get('rol', 'USUARIO')
    
    if rol_usuario == 'USUARIO':
        # Solo mostrar información, sin permitir cargas
        st.markdown("## 📁 Visualización de Carga de Archivos")
        
        st.info("""
        👤 **Acceso de Usuario:**
        - Puedes **visualizar** el estado de archivos cargados
        - **No puedes cargar** nuevos archivos
        - **No puedes gestionar** referencias
        
        📞 **Para cargar archivos:** Contacta a un administrador
        """)
        
        # Solo mostrar la pestaña de procesamiento (solo lectura)
        mostrar_procesamiento_tiempo_real()
    
    else:
        # Para administradores, mostrar interfaz completa
        mostrar_interfaz_carga()







def mostrar_parametros_sistema_admin():
    """Parámetros del sistema - SOLO para SUPERUSUARIOS"""
    
    st.markdown("#### ⚙️ Parámetros del Sistema")
    st.markdown("🔒 **Acceso de Administrador** - Configuración técnica avanzada")
    
    # Advertencia de seguridad
    st.warning("""
    ⚠️ **ATENCIÓN:** Estos parámetros afectan el rendimiento del sistema.
    Cambios incorrectos pueden causar problemas de estabilidad.
    """)
    
    with st.expander("ℹ️ ¿Qué significan estos parámetros?", expanded=False):
        st.markdown("""
        **🔢 Tamaño de lote:**
        - Cantidad de registros procesados simultáneamente
        - **Menor valor** = Menos memoria, más lento
        - **Mayor valor** = Más memoria, más rápido
        
        **⏱️ Timeout de consultas:**
        - Tiempo máximo para consultas SQL (segundos)
        - Evita consultas que se "cuelguen"
        
        **🧵 Número de hilos:**
        - Procesos paralelos para normalización
        - **Más hilos** = Más velocidad, más CPU
        - **Menos hilos** = Menos recursos, más estable
        
        **💾 TTL de cache:**
        - Tiempo que se guardan resultados en memoria
        - **Mayor TTL** = Menos consultas, datos menos frescos
        - **Menor TTL** = Más consultas, datos más actualizados
        """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**⚡ Rendimiento:**")
        batch_size = st.number_input(
            "🔢 Tamaño de lote para procesamiento:", 
            value=1000, 
            min_value=100, 
            max_value=10000,
            step=100,
            help="Registros procesados por lote. Más alto = más memoria pero más rápido."
        )
        
        timeout_seconds = st.number_input(
            "⏱️ Timeout de consultas (segundos):", 
            value=30, 
            min_value=5, 
            max_value=300,
            step=5,
            help="Tiempo máximo para una consulta SQL antes de cancelarla."
        )
    
    with col2:
        st.markdown("**🔧 Concurrencia:**")
        max_workers = st.number_input(
            "🧵 Número máximo de hilos:", 
            value=4, 
            min_value=1, 
            max_value=16,
            step=1,
            help="Procesos paralelos. Más hilos = más velocidad pero más CPU."
        )
        
        cache_ttl = st.number_input(
            "💾 TTL de cache (segundos):", 
            value=300, 
            min_value=60, 
            max_value=3600,
            step=30,
            help="Tiempo que los resultados se mantienen en memoria."
        )
    
    # Recomendaciones automáticas
    st.markdown("#### 💡 Recomendaciones Automáticas:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📱 Configurar para archivos pequeños", help="< 1,000 registros"):
            st.session_state.config_sugerida = {
                'batch_size': 500,
                'timeout': 15,
                'workers': 2,
                'cache': 300
            }
            st.success("✅ Configuración aplicada para archivos pequeños")
    
    with col2:
        if st.button("📊 Configurar para archivos medianos", help="1,000 - 10,000 registros"):
            st.session_state.config_sugerida = {
                'batch_size': 1000,
                'timeout': 30,
                'workers': 4,
                'cache': 300
            }
            st.success("✅ Configuración aplicada para archivos medianos")
    
    with col3:
        if st.button("📈 Configurar para archivos grandes", help="> 10,000 registros"):
            st.session_state.config_sugerida = {
                'batch_size': 2000,
                'timeout': 60,
                'workers': 6,
                'cache': 600
            }
            st.success("✅ Configuración aplicada para archivos grandes")
    
    # Botón para guardar configuración
    if st.button("💾 Guardar Configuración", type="primary"):
        # Guardar en base de datos o archivo de configuración
        guardar_configuracion_sistema(batch_size, timeout_seconds, max_workers, cache_ttl)
        st.success("✅ Configuración guardada correctamente")
        
        # Mostrar resumen de lo guardado
        st.info(f"""
        **Configuración guardada:**
        - 🔢 Lote: {batch_size:,} registros
        - ⏱️ Timeout: {timeout_seconds} segundos
        - 🧵 Hilos: {max_workers}
        - 💾 Cache: {cache_ttl} segundos
        """)


def mostrar_mensaje_permisos_parametros(rol_usuario):
    """Mensaje para usuarios sin permisos para ver parámetros"""
    
    st.markdown("#### ⚙️ Parámetros del Sistema")
    
    # Mensaje diferente según el rol
    if rol_usuario == 'GERENTE':
        st.warning("""
        👨‍💼 **Acceso de Gerente:**
        
        Los parámetros técnicos del sistema solo pueden ser modificados por el **SUPERUSUARIO**.
        
        **¿Por qué?**
        - Cambios incorrectos pueden afectar la estabilidad
        - Requieren conocimiento técnico avanzado
        - Pueden impactar el rendimiento de todos los usuarios
        
        📞 **¿Necesitas cambiar algo?** Contacta al administrador del sistema.
        """)
    else:
        st.info("""
        👤 **Acceso de Usuario:**
        
        Esta sección contiene configuraciones técnicas avanzadas del sistema.
        
        **Solo el administrador (SUPERUSUARIO) puede:**
        - Ver parámetros de rendimiento
        - Modificar configuraciones de la base de datos
        - Ajustar configuraciones de procesamiento
        
        📞 **¿Problemas de rendimiento?** Reporta al administrador.
        """)
    
    # Mostrar información básica que sí pueden ver
    st.markdown("---")
    st.markdown("#### ℹ️ Información Disponible:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("""
        **✅ Puedes ver:**
        - Estado de la conexión
        - Estadísticas de tablas
        - Información de la base de datos
        """)
    
    with col2:
        st.error("""
        **❌ No puedes modificar:**
        - Parámetros de rendimiento
        - Configuración de hilos
        - Timeouts del sistema
        """)


def guardar_configuracion_sistema(batch_size, timeout, workers, cache_ttl):
    """Guardar configuración del sistema en base de datos"""
    
    try:
        sistema = SistemaNormalizacion()
        usuario_actual = st.session_state.get('usuario_actual', {})
        
        # Crear tabla de configuración si no existe
        with sistema.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS configuracion_sistema (
                    id SERIAL PRIMARY KEY,
                    parametro VARCHAR(50) UNIQUE NOT NULL,
                    valor VARCHAR(100) NOT NULL,
                    descripcion TEXT,
                    modificado_por UUID REFERENCES usuarios(id_usuario),
                    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Insertar o actualizar parámetros
            parametros = [
                ('batch_size', str(batch_size), 'Tamaño de lote para procesamiento'),
                ('timeout_seconds', str(timeout), 'Timeout de consultas en segundos'),
                ('max_workers', str(workers), 'Número máximo de hilos'),
                ('cache_ttl', str(cache_ttl), 'TTL de cache en segundos')
            ]
            
            for param, valor, desc in parametros:
                conn.execute(text("""
                    INSERT INTO configuracion_sistema (parametro, valor, descripcion, modificado_por)
                    VALUES (:param, :valor, :desc, :user_id)
                    ON CONFLICT (parametro) 
                    DO UPDATE SET 
                        valor = EXCLUDED.valor,
                        modificado_por = EXCLUDED.modificado_por,
                        fecha_modificacion = CURRENT_TIMESTAMP
                """), {
                    'param': param,
                    'valor': valor,
                    'desc': desc,
                    'user_id': usuario_actual.get('id_usuario')
                })
            
            conn.commit()
        
        return True
    
    except Exception as e:
        st.error(f"Error guardando configuración: {e}")
        return False






def cargar_referencias_con_actualizacion_automatica(df_ref, tipo_ref, fuente_ref, nombre_archivo):
    """
    Función de carga que fuerza la actualización de la interfaz
    AGREGAR ESTA NUEVA FUNCIÓN
    """
    
    try:
        import psycopg2
        
        # Validar datos básicos
        if 'nombre_oficial' not in df_ref.columns or 'codigo_oficial' not in df_ref.columns:
            st.error("❌ Faltan columnas requeridas")
            return False
        
        registros_vacios = df_ref['nombre_oficial'].isna().sum() + (df_ref['nombre_oficial'] == '').sum()
        if registros_vacios > 0:
            st.error(f"❌ Hay {registros_vacios} registros sin nombre oficial")
            return False
        
        # Conectar con psycopg2
        st.info("🔌 Conectando a PostgreSQL...")
        
        conn = psycopg2.connect(
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port'],
            database=DATABASE_CONFIG['database'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password']
        )
        
        cursor = conn.cursor()
        
        # Contar referencias existentes
        st.info("📊 Contando referencias existentes...")
        cursor.execute("SELECT COUNT(*) FROM referencias_normalizacion WHERE tipo_catalogo = %s", (tipo_ref,))
        total_existentes = cursor.fetchone()[0]
        
        if total_existentes > 0:
            st.warning(f"⚠️ Se reemplazarán {total_existentes:,} referencias existentes de {tipo_ref}")
        
        # ELIMINAR referencias existentes
        if total_existentes > 0:
            st.info(f"🗑️ Eliminando {total_existentes:,} referencias existentes...")
            cursor.execute("DELETE FROM referencias_normalizacion WHERE tipo_catalogo = %s", (tipo_ref,))
            eliminados = cursor.rowcount
            st.info(f"✅ Eliminados: {eliminados:,}")
            
            # Verificar eliminación
            cursor.execute("SELECT COUNT(*) FROM referencias_normalizacion WHERE tipo_catalogo = %s", (tipo_ref,))
            verificacion = cursor.fetchone()[0]
            
            if verificacion > 0:
                st.error(f"❌ DELETE falló - quedan {verificacion:,} registros")
                conn.close()
                return False
        
        # INSERTAR nuevas referencias
        st.info(f"📥 Insertando {len(df_ref):,} nuevas referencias...")
        
        # Crear barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        insertados = 0
        timestamp_carga = datetime.now()
        
        for idx, row in df_ref.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO referencias_normalizacion 
                    (tipo_catalogo, codigo_oficial, nombre_oficial, nombre_alternativo, 
                     coordenadas_lat, coordenadas_lng, estado_padre, municipio_padre, 
                     activo, fecha_actualizacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    tipo_ref,
                    str(row.get('codigo_oficial', f'AUTO_{idx}')),
                    str(row.get('nombre_oficial', '')).strip(),
                    json.dumps(row.get('nombres_alternativos', [])) if 'nombres_alternativos' in row else None,
                    float(row['coordenadas_lat']) if 'coordenadas_lat' in row and pd.notna(row['coordenadas_lat']) else None,
                    float(row['coordenadas_lng']) if 'coordenadas_lng' in row and pd.notna(row['coordenadas_lng']) else None,
                    str(row.get('estado_padre', '')) if 'estado_padre' in row and pd.notna(row.get('estado_padre')) else None,
                    str(row.get('municipio_padre', '')) if 'municipio_padre' in row and pd.notna(row.get('municipio_padre')) else None,
                    True,
                    timestamp_carga
                ))
                
                insertados += 1
                
                # Actualizar progreso cada 50 registros
                if insertados % 50 == 0:
                    progress = insertados / len(df_ref)
                    progress_bar.progress(progress)
                    status_text.text(f"📥 Insertados: {insertados:,} / {len(df_ref):,} ({progress:.1%})")
                
            except Exception as e:
                st.warning(f"⚠️ Error en registro {idx}: {str(e)}")
        
        # Finalizar progreso
        progress_bar.progress(1.0)
        status_text.text(f"✅ Insertados: {insertados:,} registros")
        
        # COMMIT CRÍTICO
        st.info("💾 Guardando cambios...")
        conn.commit()
        
        # VERIFICACIÓN FINAL
        st.info("🔍 Verificando resultado...")
        cursor.execute("SELECT COUNT(*) FROM referencias_normalizacion WHERE tipo_catalogo = %s", (tipo_ref,))
        total_final = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM referencias_normalizacion")
        total_global = cursor.fetchone()[0]
        
        conn.close()
        
        # MOSTRAR RESULTADO FINAL
        if total_final == insertados:
            st.success(f"""
            ## 🎉 CARGA EXITOSA
            
            **✅ Resultado:**
            - **Eliminadas:** {total_existentes:,} referencias anteriores
            - **Insertadas:** {insertados:,} nuevas referencias  
            - **Total {tipo_ref}:** {total_final:,} referencias
            - **Total sistema:** {total_global:,} referencias
            
            **🔄 La tabla se actualizará automáticamente...**
            """)
            
            # MARCAR EN SESSION STATE QUE HUBO CAMBIOS
            if 'referencias_actualizadas' not in st.session_state:
                st.session_state.referencias_actualizadas = 0
            st.session_state.referencias_actualizadas += 1
            
            return True
        else:
            st.error(f"❌ Discrepancia: insertados {insertados:,}, final {total_final:,}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error en carga: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False





# ========================================
# 10. EJECUCIÓN PRINCIPAL
# ========================================

if __name__ == "__main__":
    #main()
    main_con_autenticacion()
 
