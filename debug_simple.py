# ========================================
# ARCHIVO: debug_simple.py
# PROPÓSITO: Diagnosticar por qué no funciona
# ========================================

"""
💡 Este archivo nos ayuda a encontrar qué está fallando
Vamos a probar cada cosa paso a paso
"""

print("🚀 INICIANDO DIAGNÓSTICO...")
print("=" * 40)

# ========================================
# PRUEBA 1: Python básico
# ========================================

print("🔍 PRUEBA 1: Python básico")
print("   ✅ Python funciona (si ves este mensaje)")

# ========================================
# PRUEBA 2: Importar librerías
# ========================================

print("\n🔍 PRUEBA 2: Importando librerías...")

try:
    import pandas as pd
    print("   ✅ pandas importado correctamente")
except ImportError as e:
    print(f"   ❌ Error con pandas: {e}")

try:
    import os
    print("   ✅ os importado correctamente")
except ImportError as e:
    print(f"   ❌ Error con os: {e}")

# ========================================
# PRUEBA 3: Crear carpeta simple
# ========================================

print("\n🔍 PRUEBA 3: Creando carpeta de prueba...")

try:
    os.makedirs("test_carpeta", exist_ok=True)
    print("   ✅ Carpeta creada correctamente")
    
    # Verificar que existe
    if os.path.exists("test_carpeta"):
        print("   ✅ Carpeta verificada")
    else:
        print("   ❌ Carpeta no se encontró")
        
except Exception as e:
    print(f"   ❌ Error creando carpeta: {e}")

# ========================================
# PRUEBA 4: Importar config.py
# ========================================

print("\n🔍 PRUEBA 4: Importando config.py...")

try:
    from config import PATHS, FILES
    print("   ✅ config.py importado correctamente")
    print(f"   📁 Encontradas {len(PATHS)} rutas configuradas")
except ImportError as e:
    print(f"   ❌ Error importando config.py: {e}")
    print("   💡 Asegúrate que config.py esté en la misma carpeta")
except Exception as e:
    print(f"   ❌ Error en config.py: {e}")

# ========================================
# PRUEBA 5: Crear DataFrame simple
# ========================================

print("\n🔍 PRUEBA 5: Creando DataFrame de prueba...")

try:
    # Datos súper simples
    datos = [
        ['DES', 'DDS', '01', 'AGUASCALIENTES'],
        ['DES', 'DDS', '02', 'BAJA CALIFORNIA']
    ]
    
    df = pd.DataFrame(datos, columns=['division', 'esquema', 'clave', 'nombre'])
    print("   ✅ DataFrame creado correctamente")
    print(f"   📊 DataFrame tiene {len(df)} filas")
    
except Exception as e:
    print(f"   ❌ Error creando DataFrame: {e}")

# ========================================
# PRUEBA 6: Guardar archivo CSV
# ========================================

print("\n🔍 PRUEBA 6: Guardando archivo CSV de prueba...")

try:
    # Usar el DataFrame de la prueba anterior
    df.to_csv("test_archivo.csv", index=False)
    print("   ✅ Archivo CSV guardado")
    
    # Verificar que existe
    if os.path.exists("test_archivo.csv"):
        print("   ✅ Archivo verificado")
        
        # Leer el archivo para verificar contenido
        df_leido = pd.read_csv("test_archivo.csv")
        print(f"   ✅ Archivo leído - {len(df_leido)} filas")
    else:
        print("   ❌ Archivo no encontrado")
        
except Exception as e:
    print(f"   ❌ Error con archivo CSV: {e}")

# ========================================
# PRUEBA 7: Limpiar archivos de prueba
# ========================================

print("\n🧹 LIMPIANDO archivos de prueba...")

try:
    if os.path.exists("test_archivo.csv"):
        os.remove("test_archivo.csv")
        print("   ✅ test_archivo.csv eliminado")
    
    if os.path.exists("test_carpeta"):
        os.rmdir("test_carpeta")
        print("   ✅ test_carpeta eliminada")
        
except Exception as e:
    print(f"   ⚠️  Error limpiando: {e}")

# ========================================
# RESUMEN
# ========================================

print("\n📋 RESUMEN DEL DIAGNÓSTICO:")
print("=" * 40)
print("Si todas las pruebas salieron con ✅, entonces:")
print("💡 El problema está en crear_datos_prueba.py")
print("🔧 Vamos a crear una versión simplificada")

print("\nSi alguna prueba salió con ❌:")
print("💡 Ese es el problema que necesitamos solucionar")

print("\n🎯 PRÓXIMO PASO:")
print("Ejecuta este diagnóstico y compárteme los resultados")