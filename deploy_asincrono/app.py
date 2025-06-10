# ========================================
# app.py - PUNTO DE ENTRADA PARA RAILWAY
# Sistema Asíncrono
# ========================================

import streamlit as st
import os
import sys
from pathlib import Path

# Configurar página
st.set_page_config(
    page_title="🔄 Sistema Asíncrono - Telmex",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Detectar ambiente
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None

def main():
    """Función principal específica para Sistema Asíncrono"""
    
    try:
        # Mostrar información del sistema
        with st.sidebar:
            st.success("🔄 **Sistema Asíncrono**")
            st.caption("Sistema de procesamiento en cola")
            if IS_RAILWAY:
                st.success("🚂 Railway Production")
            else:
                st.info("🏠 Desarrollo Local")
        
        # Importar y ejecutar sistema asíncrono
        from async_processor.dashboard import show_unified_dashboard
        from sistema_completo_normalizacion import (
            inicializar_sistema_usuarios, 
            verificar_autenticacion, 
            mostrar_pantalla_login, 
            mostrar_barra_usuario
        )
        
        # Inicializar usuarios y verificar autenticación
        inicializar_sistema_usuarios()
        
        if not verificar_autenticacion():
            st.markdown("## 🔐 Acceso al Sistema Asíncrono")
            mostrar_pantalla_login()
            return
        
        # Mostrar interfaz asíncrona
        mostrar_barra_usuario()
        show_unified_dashboard()
    
    except ImportError as e:
        st.error(f"""
        ❌ **Error de importación:** {str(e)}
        
        Verifica que todos los archivos estén presentes en Railway.
        """)
    
    except Exception as e:
        st.error(f"""
        ❌ **Error:** {str(e)}
        
        **Información del ambiente:**
        - Railway: {IS_RAILWAY}
        - Directorio: {os.getcwd()}
        """)

if __name__ == "__main__":
    main()
