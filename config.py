# ========================================
# 1. INFORMACIÓN DE LA BASE DE DATOS
# ========================================

# 💡 Esta es la información para conectarnos a PostgreSQL
# Es como tener la dirección y llave de una casa
DATABASE_CONFIG = {
    'host': 'localhost',        # 🏠 Dirección: tu computadora
    'port': 5432,              # 🚪 Puerto: puerta específica (siempre es 5432 para PostgreSQL)
    'database': 'normalizacion_domicilios',  # 📦 Nombre de nuestra caja fuerte de datos
    'user': 'postgres',        # 👤 Usuario (como tu nombre de usuario)
    'password': 'admin123'     # 🔑 Contraseña (CAMBIA ESTA por la tuya)
}

# ⚠️  IMPORTANTE: Cambia 'admin123' por la contraseña que pusiste cuando instalaste PostgreSQL

# ========================================
# 2. RUTAS DE ARCHIVOS Y CARPETAS
# ========================================

# 💡 Aquí definimos dónde están todas nuestras carpetas
# Es como tener un mapa de tu casa
PATHS = {
    # 📁 Carpetas principales
    'data_raw': 'data/raw/',                    # Datos originales de AS400
    'data_reference': 'data/reference/',         # Datos de SEPOMEX (referencia)
    'data_processed': 'data/processed/',         # Datos ya limpiados
    
    # 📁 Carpetas específicas para DES
    'des_raw': 'data/raw/DES/',
    'des_processed': 'data/processed/DES/',
    
    # 📁 Carpetas de SEPOMEX
    'sepomex': 'data/reference/sepomex/',
    
    # 📁 Otras carpetas importantes
    'dashboard': 'dashboard/',
    'logs': 'logs/'                             # Para guardar registros de lo que pasa
}

# ========================================
# 3. NOMBRES DE ARCHIVOS
# ========================================

# 💡 Los nombres exactos de archivos que vamos a usar
# Si cambias el nombre de un archivo, solo lo cambias aquí
FILES = {
    # 📄 Archivos que vendrán de AS400
    'estados_dds': 'estados_dds.csv',
    'estados_db2': 'estados_db2.csv',
    
    # 📄 Archivos de referencia SEPOMEX
    'estados_sepomex': 'estados_sepomex.csv',
    'coordenadas': 'coordenadas.csv',
    
    # 📄 Archivos de resultados
    'estados_normalizados': 'estados_normalizados.csv',
    'reporte_calidad': 'reporte_calidad.xlsx'
}

# ========================================
# 4. CONFIGURACIÓN DEL ALGORITMO
# ========================================

# 💡 Aquí ponemos los "niveles de exigencia" de nuestro algoritmo
# Es como decidir qué tan estricto vas a ser calificando un examen
MATCHING_CONFIG = {
    'umbral_exacto': 1.0,           # 100% - Tiene que ser idéntico
    'umbral_fuzzy_alto': 0.8,       # 80% - Muy parecido
    'umbral_fuzzy_bajo': 0.6,       # 60% - Parecido
    'umbral_revision': 0.5,         # 50% - Necesita que un humano lo revise
}

# ========================================
# 5. CONFIGURACIÓN DEL DASHBOARD
# ========================================

# 💡 Configuración para nuestra página web bonita
DASHBOARD_CONFIG = {
    'titulo': 'Normalización de Domicilios',
    'puerto': 8501,                 # 🌐 Puerto donde se abrirá la página web
    'tema': 'dark',                 # 🎨 Tema oscuro (como Netflix)
    'actualizacion_segundos': 30,   # ⏰ Cada cuánto se actualiza automáticamente
}

# ========================================
# 6. MENSAJES PARA EL USUARIO
# ========================================

# 💡 Mensajes que aparecerán en la pantalla
# Es mejor tenerlos aquí organizados que repartidos por todo el código
MESSAGES = {
    'inicio': '🚀 Iniciando proceso de normalización...',
    'exito': '✅ Proceso completado exitosamente',
    'error_db': '❌ No se pudo conectar a la base de datos',
    'error_archivo': '❌ No se encontró el archivo',
    'procesando': '🔄 Procesando registros...',
    'validacion': '📋 Registros que requieren validación manual',
}

# ========================================
# 7. COLORES PARA EL DASHBOARD
# ========================================

# 💡 Paleta de colores para que se vea bonito y profesional
COLORS = {
    'primary': '#1f77b4',      # Azul principal
    'success': '#2ca02c',      # Verde para éxito
    'warning': '#ff7f0e',      # Naranja para advertencias  
    'error': '#d62728',        # Rojo para errores
    'info': '#17becf',         # Cyan para información
    'background': '#0e1117',   # Fondo oscuro
    'text': '#ffffff',         # Texto blanco
}

# ========================================
# 8. FUNCIÓN PARA CREAR CARPETAS
# ========================================

import os

def crear_carpetas():
    """
    💡 Esta función crea todas las carpetas que necesitamos
    Es como preparar todos los cajones antes de empezar a organizar
    
    ¿Cuándo usar esta función?
    - Al inicio del proyecto
    - Si accidentalmente borras alguna carpeta
    """
    
    print("📁 Creando estructura de carpetas...")
    
    # Crear cada carpeta de la lista PATHS
    for nombre_carpeta, ruta in PATHS.items():
        try:
            # os.makedirs crea la carpeta (y las carpetas padre si no existen)
            # exist_ok=True significa "no te enojes si la carpeta ya existe"
            os.makedirs(ruta, exist_ok=True)
            print(f"   ✅ Carpeta creada: {ruta}")
        except Exception as error:
            print(f"   ❌ Error creando {ruta}: {error}")
    
    print("📁 ¡Estructura de carpetas lista!")

# ========================================
# 9. FUNCIÓN PARA PROBAR LA CONFIGURACIÓN
# ========================================

def probar_configuracion():
    """
    💡 Esta función verifica que todo esté bien configurado
    Es como revisar que tienes todos los materiales antes de empezar un proyecto
    """
    
    print("🔍 Probando configuración...")
    
    # Probar que las carpetas existen
    carpetas_faltantes = []
    for nombre, ruta in PATHS.items():
        if not os.path.exists(ruta):
            carpetas_faltantes.append(ruta)
    
    if carpetas_faltantes:
        print("❌ Faltan estas carpetas:")
        for carpeta in carpetas_faltantes:
            print(f"   - {carpeta}")
        print("💡 Ejecuta crear_carpetas() para crearlas")
    else:
        print("✅ Todas las carpetas existen")
    
    # Probar configuración de base de datos (básico)
    if DATABASE_CONFIG['password'] == 'admin123':
        print("⚠️  Recuerda cambiar la contraseña en DATABASE_CONFIG")
    else:
        print("✅ Contraseña de base de datos configurada")
    
    print("🔍 Revisión de configuración completada")

# ========================================
# 10. SI EJECUTAS ESTE ARCHIVO DIRECTAMENTE
# ========================================

if __name__ == "__main__":
    """
    💡 Esta parte solo se ejecuta si ejecutas este archivo directamente
    Es como decir "si alguien ejecuta este archivo, haz esto"
    """
    
    print("🎯 Ejecutando configuración inicial...")
    crear_carpetas()
    probar_configuracion()
    print("🎉 ¡Configuración lista para usar!")