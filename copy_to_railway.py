# ========================================
# PASO 4: SCRIPT DE COPIA AUTOMÁTICA
# Crear archivo: copy_to_railway.py
# ========================================

import shutil
import os
from datetime import datetime

def copy_to_railway():
    """Script para copiar automáticamente el archivo maestro"""
    
    source = "sistema_completo_normalizacion.py"
    target = "app.py"
    
    print("🚀 Iniciando copia de archivo maestro...")
    
    if not os.path.exists(source):
        print(f"❌ Error: No se encuentra {source}")
        return False
    
    try:
        # Crear backup del app.py anterior
        if os.path.exists(target):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup = f"app_backup_{timestamp}.py"
            shutil.copy2(target, backup)
            print(f"📦 Backup creado: {backup}")
        
        # Copiar archivo maestro
        shutil.copy2(source, target)
        print(f"✅ Copiado: {source} → {target}")
        
        # Verificar integridad
        with open(source, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        with open(target, 'r', encoding='utf-8') as f:
            target_content = f.read()
        
        if source_content == target_content:
            lines = len(source_content.splitlines())
            size_kb = len(source_content.encode('utf-8')) / 1024
            
            print("🎯 Verificación: Archivos idénticos ✅")
            print(f"📊 Estadísticas: {lines:,} líneas, {size_kb:.1f} KB")
            print("\n✅ ¡Listo para Railway!")
            print("\n📋 Comandos Git sugeridos:")
            print("  git add app.py")
            print("  git commit -m 'Update: Sync from master file'")
            print("  git push")
            
            return True
        else:
            print("❌ Error: Los archivos no son idénticos")
            return False
    
    except Exception as e:
        print(f"❌ Error copiando: {str(e)}")
        return False

if __name__ == "__main__":
    copy_to_railway()