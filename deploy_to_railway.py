# ========================================
# deploy_to_railway.py - SCRIPT UNIFICADO PARA RAILWAY
# Sistema de 3 Proyectos: Síncrono, Asíncrono e Híbrido
# ========================================

import shutil
import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ========================================
# CONFIGURACIÓN DE PROYECTOS
# ========================================

PROJECTS_CONFIG = {
    "sincrono": {
        "name": "Sistema Síncrono",
        "source_file": "sistema_completo_normalizacion.py",
        "target_file": "app.py",
        "description": "Sistema de procesamiento inmediato",
        "emoji": "⚡",
        "railway_service": "sistema-sincrono"
    },
    "asincrono": {
        "name": "Sistema Asíncrono", 
        "source_file": "async_processor/dashboard.py",
        "target_file": "app.py",
        "description": "Sistema de procesamiento en cola",
        "emoji": "🔄",
        "railway_service": "sistema-asincrono"
    },
    "hibrido": {
        "name": "Sistema Híbrido",
        "source_file": "app_launcher.py", 
        "target_file": "app.py",
        "description": "Sistema unificado con detección automática",
        "emoji": "🔀",
        "railway_service": "sistema-hibrido"
    }
}

# ========================================
# CLASE PRINCIPAL DEL DEPLOYER
# ========================================

class RailwayDeployer:
    """Deployer unificado para los 3 sistemas"""
    
    def __init__(self):
        self.is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
        self.current_dir = Path.cwd()
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"🚀 Railway Deployer Unificado")
        print(f"📁 Directorio: {self.current_dir}")
        print(f"🌍 Ambiente: {'Railway' if self.is_railway else 'Local'}")
        print("=" * 60)
    
    def deploy_all(self):
        """Deployar todos los sistemas"""
        
        print("🚀 INICIANDO DEPLOY DE TODOS LOS SISTEMAS")
        print("=" * 60)
        
        resultados = {}
        
        for project_key, config in PROJECTS_CONFIG.items():
            print(f"\n{config['emoji']} Procesando: {config['name']}")
            print("-" * 40)
            
            resultado = self.deploy_single_project(project_key, config)
            resultados[project_key] = resultado
        
        # Mostrar resumen final
        self.mostrar_resumen_deploy(resultados)
        
        return resultados
    
    def deploy_single_project(self, project_key, config):
        """Deployar un proyecto específico"""
        
        try:
            # Verificar archivos fuente
            if not self.verificar_archivos_fuente(config):
                return {"success": False, "error": "Archivos fuente faltantes"}
            
            # Crear estructura del proyecto
            project_dir = self.crear_estructura_proyecto(project_key, config)
            
            # Copiar archivos necesarios
            self.copiar_archivos_proyecto(project_dir, project_key, config)
            
            # Crear archivos específicos del proyecto
            self.crear_archivos_especificos(project_dir, project_key, config)
            
            # Verificar integridad
            if self.verificar_integridad_proyecto(project_dir, config):
                print(f"✅ {config['name']}: Deploy exitoso")
                return {
                    "success": True, 
                    "project_dir": str(project_dir),
                    "files_created": self.contar_archivos(project_dir)
                }
            else:
                return {"success": False, "error": "Verificación de integridad falló"}
        
        except Exception as e:
            print(f"❌ Error en {config['name']}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def verificar_archivos_fuente(self, config):
        """Verificar que existan los archivos fuente necesarios"""
        
        archivos_requeridos = [
            config['source_file'],
            'requirements.txt',
            'sistema_completo_normalizacion.py'  # Siempre necesario como dependencia
        ]
        
        # Archivos adicionales según el tipo
        if 'async' in config['source_file']:
            archivos_requeridos.extend([
                'async_processor/core.py',
                'async_processor/config.py',
                'async_processor/utils.py',
                'async_processor/queue_manager.py'
            ])
        
        if 'launcher' in config['source_file']:
            archivos_requeridos.extend([
                'async_processor/dashboard.py'
            ])
        
        archivos_faltantes = []
        for archivo in archivos_requeridos:
            if not Path(archivo).exists():
                archivos_faltantes.append(archivo)
        
        if archivos_faltantes:
            print(f"❌ Archivos faltantes: {', '.join(archivos_faltantes)}")
            return False
        
        print(f"✅ Todos los archivos fuente verificados")
        return True
    
    def crear_estructura_proyecto(self, project_key, config):
        """Crear estructura de directorios para el proyecto"""
        
        project_dir = self.current_dir / f"deploy_{project_key}"
        
        # Limpiar directorio anterior si existe
        if project_dir.exists():
            shutil.rmtree(project_dir)
        
        # Crear estructura básica
        project_dir.mkdir()
        (project_dir / 'async_processor').mkdir(exist_ok=True)
        
        print(f"📁 Estructura creada: {project_dir}")
        return project_dir
    
    def copiar_archivos_proyecto(self, project_dir, project_key, config):
        """Copiar archivos necesarios para el proyecto"""
        
        # 1. Crear app.py principal basado en el tipo de proyecto
        self.crear_app_py_especifico(project_dir, project_key, config)
        
        # 2. Copiar archivos comunes
        archivos_comunes = [
            'sistema_completo_normalizacion.py',
            'requirements.txt'
        ]
        
        for archivo in archivos_comunes:
            if Path(archivo).exists():
                shutil.copy2(archivo, project_dir / archivo)
                print(f"📄 Copiado: {archivo}")
        
        # 3. Copiar archivos específicos según el tipo
        if project_key in ['asincrono', 'hibrido']:
            # Copiar todo el directorio async_processor
            async_files = [
                'async_processor/dashboard.py',
                'async_processor/core.py', 
                'async_processor/config.py',
                'async_processor/utils.py',
                'async_processor/queue_manager.py'
            ]
            
            for archivo in async_files:
                if Path(archivo).exists():
                    target_path = project_dir / archivo
                    target_path.parent.mkdir(exist_ok=True)
                    shutil.copy2(archivo, target_path)
                    print(f"📄 Copiado: {archivo}")
            
            # Crear __init__.py en async_processor
            (project_dir / 'async_processor' / '__init__.py').touch()
        
        # 4. Copiar launcher si es híbrido
        if project_key == 'hibrido':
            if Path('app_launcher.py').exists():
                shutil.copy2('app_launcher.py', project_dir / 'app_launcher.py')
                print(f"📄 Copiado: app_launcher.py")
        
        # 5. Copiar archivos opcionales
        archivos_opcionales = ['logo_RN.png', '.env.example', 'README.md']
        for archivo in archivos_opcionales:
            if Path(archivo).exists():
                shutil.copy2(archivo, project_dir / archivo)
                print(f"📄 Copiado (opcional): {archivo}")
    
    def crear_app_py_especifico(self, project_dir, project_key, config):
        """Crear app.py específico para cada tipo de proyecto"""
        
        app_content = self.generar_app_py_content(project_key, config)
        
        app_path = project_dir / 'app.py'
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(app_content)
        
        print(f"📄 Creado: app.py para {config['name']}")
    
    def generar_app_py_content(self, project_key, config):
        """Generar contenido específico de app.py según el tipo"""
        
        base_imports = '''# ========================================
# app.py - PUNTO DE ENTRADA PARA RAILWAY
# {name}
# ========================================

import streamlit as st
import os
import sys
from pathlib import Path

# Configurar página
st.set_page_config(
    page_title="{emoji} {name} - Telmex",
    page_icon="{emoji}",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Detectar ambiente
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None

def main():
    """Función principal específica para {name}"""
    
    try:
        # Mostrar información del sistema
        with st.sidebar:
            st.success("{emoji} **{name}**")
            st.caption("{description}")
            if IS_RAILWAY:
                st.success("🚂 Railway Production")
            else:
                st.info("🏠 Desarrollo Local")
        
'''.format(
            name=config['name'],
            emoji=config['emoji'], 
            description=config['description']
        )
        
        # Contenido específico según el tipo
        if project_key == 'sincrono':
            specific_content = '''        # Importar y ejecutar sistema síncrono
        from sistema_completo_normalizacion import main_con_autenticacion
        main_con_autenticacion()
'''
        
        elif project_key == 'asincrono':
            specific_content = '''        # Importar y ejecutar sistema asíncrono
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
'''
        
        elif project_key == 'hibrido':
            specific_content = '''        # Importar y ejecutar launcher híbrido
        from app_launcher import main as launcher_main
        launcher_main()
'''
        
        # Contenido final común
        final_content = '''    
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
'''
        
        return base_imports + specific_content + final_content
    
    def crear_archivos_especificos(self, project_dir, project_key, config):
        """Crear archivos específicos según el proyecto"""
        
        # 1. Crear railway.json específico
        self.crear_railway_json(project_dir, project_key, config)
        
        # 2. Crear README.md específico
        self.crear_readme_especifico(project_dir, project_key, config)
        
        # 3. Crear .env.example específico
        self.crear_env_example(project_dir, project_key, config)
    
    def crear_railway_json(self, project_dir, project_key, config):
        """Crear configuración específica de Railway"""
        
        railway_config = {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "NIXPACKS",
                "buildCommand": "pip install -r requirements.txt"
            },
            "deploy": {
                "startCommand": f"streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true",
                "healthcheckPath": "/",
                "healthcheckTimeout": 300
            },
            "environments": {
                "production": {
                    "variables": {
                        "PYTHONPATH": "/app",
                        "STREAMLIT_SERVER_HEADLESS": "true",
                        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
                        "PROJECT_TYPE": project_key.upper()
                    }
                }
            }
        }
        
        with open(project_dir / 'railway.json', 'w', encoding='utf-8') as f:
            json.dump(railway_config, f, indent=2)
        
        print(f"📄 Creado: railway.json para {config['name']}")
    
    def crear_readme_especifico(self, project_dir, project_key, config):
        """Crear README específico para cada proyecto"""
        
        readme_content = f'''# {config['emoji']} {config['name']} - Telmex

{config['description']}

## 🚀 Deploy en Railway

Este proyecto está configurado específicamente para **{config['name']}**.

### Variables de Entorno Requeridas:
- `DATABASE_URL`: URL completa de PostgreSQL
- `PORT`: Puerto (Railway lo asigna automáticamente)

### Comando de Deploy:
```bash
git add .
git commit -m "Deploy {config['name']}"
git push
```

### Características:
- {config['emoji']} **Tipo:** {config['name']}
- 🚂 **Optimizado para Railway**
- 🔒 **Sistema de autenticación integrado**
- 📊 **PostgreSQL como base de datos**

### Estructura del Proyecto:
```
{project_key}/
├── app.py                              ← Punto de entrada
├── sistema_completo_normalizacion.py   ← Sistema principal
├── requirements.txt                    ← Dependencias
├── railway.json                        ← Configuración Railway
└── README.md                          ← Este archivo
```

### Para Desarrollo Local:
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Soporte:
- 📧 Contacta al equipo de desarrollo para soporte
- 🔧 Logs disponibles en Railway Dashboard
'''
        
        # Agregar información específica según el tipo
        if project_key == 'asincrono':
            readme_content += '''
### Características Específicas del Sistema Asíncrono:
- 🔄 Procesamiento en cola con workers
- 📊 Monitoreo en tiempo real
- ⚡ No bloquea la interfaz de usuario
- 🎯 Ideal para archivos grandes (>5,000 registros)
'''
        
        elif project_key == 'hibrido':
            readme_content += '''
### Características Específicas del Sistema Híbrido:
- 🔀 Detección automática de modo (síncrono/asíncrono)
- 🚀 Launcher unificado con 3 opciones
- 📊 Dashboard completo con todas las funcionalidades
- 🎯 Ideal para uso general y producción
'''
        
        with open(project_dir / 'README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"📄 Creado: README.md para {config['name']}")
    
    def crear_env_example(self, project_dir, project_key, config):
        """Crear archivo .env.example"""
        
        env_content = f'''# Archivo de ejemplo de variables de entorno
# Para {config['name']}

# Base de datos (REQUERIDO)
DATABASE_URL=postgresql://username:password@host:port/database

# Puerto (Railway lo asigna automáticamente)
PORT=8080

# Configuración específica del proyecto
PROJECT_TYPE={project_key.upper()}

# Variables opcionales para desarrollo local
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=normalizacion_domicilios
LOCAL_DB_USER=postgres
LOCAL_DB_PASSWORD=admin123

# Configuración de Streamlit (opcional)
STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200
'''
        
        with open(project_dir / '.env.example', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"📄 Creado: .env.example para {config['name']}")
    
    def verificar_integridad_proyecto(self, project_dir, config):
        """Verificar integridad del proyecto creado"""
        
        archivos_requeridos = ['app.py', 'requirements.txt', 'railway.json']
        
        for archivo in archivos_requeridos:
            archivo_path = project_dir / archivo
            if not archivo_path.exists():
                print(f"❌ Falta archivo requerido: {archivo}")
                return False
            
            # Verificar que no esté vacío
            if archivo_path.stat().st_size == 0:
                print(f"❌ Archivo vacío: {archivo}")
                return False
        
        print(f"✅ Integridad verificada")
        return True
    
    def contar_archivos(self, project_dir):
        """Contar archivos creados en el proyecto"""
        
        archivos = list(project_dir.rglob('*'))
        archivos = [f for f in archivos if f.is_file()]
        
        return len(archivos)
    
    def mostrar_resumen_deploy(self, resultados):
        """Mostrar resumen final del deploy"""
        
        print("\n" + "=" * 60)
        print("📊 RESUMEN FINAL DEL DEPLOY")
        print("=" * 60)
        
        exitosos = 0
        fallidos = 0
        
        for project_key, resultado in resultados.items():
            config = PROJECTS_CONFIG[project_key]
            
            if resultado['success']:
                exitosos += 1
                print(f"✅ {config['emoji']} {config['name']}: EXITOSO")
                print(f"   📁 Directorio: {resultado['project_dir']}")
                print(f"   📄 Archivos: {resultado['files_created']}")
            else:
                fallidos += 1
                print(f"❌ {config['emoji']} {config['name']}: FALLÓ")
                print(f"   🔍 Error: {resultado['error']}")
        
        print("-" * 60)
        print(f"📈 ESTADÍSTICAS:")
        print(f"   ✅ Exitosos: {exitosos}")
        print(f"   ❌ Fallidos: {fallidos}")
        print(f"   📊 Total: {exitosos + fallidos}")
        
        if exitosos > 0:
            print("\n🚀 PRÓXIMOS PASOS:")
            print("1. Revisa los directorios creados")
            print("2. Haz commit y push de cada proyecto")
            print("3. Configura las variables de entorno en Railway")
            print("4. ¡Disfruta tus sistemas en producción!")
        
        print("=" * 60)

# ========================================
# FUNCIONES DE UTILIDAD
# ========================================

def deploy_specific_project(project_name):
    """Deployar un proyecto específico"""
    
    if project_name not in PROJECTS_CONFIG:
        print(f"❌ Proyecto '{project_name}' no válido.")
        print(f"Opciones disponibles: {', '.join(PROJECTS_CONFIG.keys())}")
        return False
    
    deployer = RailwayDeployer()
    config = PROJECTS_CONFIG[project_name]
    
    print(f"🚀 Deploying específico: {config['emoji']} {config['name']}")
    
    resultado = deployer.deploy_single_project(project_name, config)
    
    if resultado['success']:
        print(f"\n✅ {config['name']} deployado exitosamente!")
        print(f"📁 Ubicación: {resultado['project_dir']}")
        return True
    else:
        print(f"\n❌ Error deployando {config['name']}: {resultado['error']}")
        return False

def mostrar_ayuda():
    """Mostrar ayuda del script"""
    
    print("🚀 Railway Deployer Unificado - Ayuda")
    print("=" * 50)
    print("USO:")
    print("  python deploy_to_railway.py [comando] [proyecto]")
    print("")
    print("COMANDOS:")
    print("  all          - Deploy todos los proyectos")
    print("  sincrono     - Deploy solo sistema síncrono")
    print("  asincrono    - Deploy solo sistema asíncrono")
    print("  hibrido      - Deploy solo sistema híbrido")
    print("  help         - Mostrar esta ayuda")
    print("")
    print("PROYECTOS DISPONIBLES:")
    for key, config in PROJECTS_CONFIG.items():
        print(f"  {config['emoji']} {key:<12} - {config['name']}")
    print("")
    print("EJEMPLOS:")
    print("  python deploy_to_railway.py all")
    print("  python deploy_to_railway.py hibrido")

# ========================================
# FUNCIÓN PRINCIPAL
# ========================================

def main():
    """Función principal del script"""
    
    if len(sys.argv) < 2:
        print("🚀 Railway Deployer Unificado")
        print("Usa 'python deploy_to_railway.py help' para ver opciones")
        comando = "all"  # Por defecto, deploy todo
    else:
        comando = sys.argv[1].lower()
    
    if comando == 'help':
        mostrar_ayuda()
    elif comando == 'all':
        deployer = RailwayDeployer()
        deployer.deploy_all()
    elif comando in PROJECTS_CONFIG:
        deploy_specific_project(comando)
    else:
        print(f"❌ Comando '{comando}' no reconocido")
        mostrar_ayuda()

if __name__ == "__main__":
    main()