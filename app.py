import os
from sistema_completo_normalizacion import main

# Detectar si estamos en Railway
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT_NAME') is not None

if __name__ == "__main__":
    if IS_RAILWAY:
        # En Railway: forzar el uso del puerto correcto
        import subprocess
        import sys
        
        port = os.getenv('PORT')
        if not port:
            print("ERROR: PORT environment variable not found")
            exit(1)
            
        print(f"Railway detected - Using PORT: {port}")
        
        # Eliminar el archivo config.toml si existe para evitar conflictos
        config_path = ".streamlit/config.toml"
        if os.path.exists(config_path):
            os.remove(config_path)
            print("Removed conflicting config.toml")
        
        # Comando con todas las configuraciones en línea
        cmd = [
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            f'--server.port={port}',
            '--server.address=0.0.0.0',
            '--server.headless=true',
            '--server.enableCORS=false',
            '--server.enableXsrfProtection=false',
            '--server.fileWatcherType=none'
        ]
        
        print(f"Starting Streamlit with command: {' '.join(cmd)}")
        subprocess.run(cmd)
    else:
        # Desarrollo local
        main()