import os
import sys

print("🪟 Diagnóstico para Windows")
print("="*50)

print(f"📂 Directorio actual: {os.getcwd()}")
print(f"🐍 Python: {sys.version}")

print("\n📁 Archivos en la raíz del proyecto:")
try:
    archivos_raiz = os.listdir('.')
    for archivo in sorted(archivos_raiz):
        if os.path.isfile(archivo):
            print(f"  📄 {archivo}")
        elif os.path.isdir(archivo):
            print(f"  📁 {archivo}/")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n📁 Archivos en la carpeta modulos:")
try:
    if os.path.exists('modulos'):
        archivos_modulos = os.listdir('modulos')
        for archivo in sorted(archivos_modulos):
            ruta_completa = os.path.join('modulos', archivo)
            if os.path.isfile(ruta_completa):
                print(f"  📄 {archivo}")
            elif os.path.isdir(ruta_completa):
                print(f"  📁 {archivo}/")
    else:
        print("  ❌ La carpeta 'modulos' no existe")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n🔍 Verificando archivos requeridos:")
archivos_requeridos = [
    'sistema_completo_normalizacion.py',
    'modulos/__init__.py',
    'modulos/auth_mejorado.py',
    'modulos/procesador_asincrono.py'
]

for archivo in archivos_requeridos:
    if os.path.exists(archivo):
        tamaño = os.path.getsize(archivo)
        print(f"  ✅ {archivo} ({tamaño} bytes)")
    else:
        print(f"  ❌ {archivo} - NO ENCONTRADO")

print("\n🧪 Intentando importar...")
try:
    from modulos import auth_mejorado
    print("  ✅ Módulo auth_mejorado importado")
except Exception as e:
    print(f"  ❌ Error: {e}")

try:
    from modulos import procesador_asincrono
    print("  ✅ Módulo procesador_asincrono importado")
except Exception as e:
    print(f"  ❌ Error: {e}")

input("\n⏸️ Presiona Enter para continuar...")