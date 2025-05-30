import os
import subprocess
import time
import requests
from threading import Thread
from flask import Flask, request, Response
import sys

app = Flask(__name__)

# Puerto donde Railway espera la aplicación
RAILWAY_PORT = int(os.environ.get('PORT', 5000))
# Puerto interno donde correrá Streamlit
STREAMLIT_PORT = 8501

def start_streamlit():
    """Inicia Streamlit en segundo plano"""
    print(f"Starting Streamlit on port {STREAMLIT_PORT}")
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'sistema_completo_normalizacion.py',
        f'--server.port={STREAMLIT_PORT}',
        '--server.address=127.0.0.1',
        '--server.headless=true',
        '--server.enableCORS=false',
        '--server.enableXsrfProtection=false'
    ]
    subprocess.run(cmd)

def wait_for_streamlit():
    """Espera a que Streamlit esté listo"""
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f'http://127.0.0.1:{STREAMLIT_PORT}', timeout=2)
            if response.status_code == 200:
                print(f"Streamlit is ready on port {STREAMLIT_PORT}")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"Waiting for Streamlit... attempt {i+1}/{max_attempts}")
        time.sleep(2)
    return False

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """Proxy todas las peticiones a Streamlit"""
    try:
        # Construir URL de destino
        target_url = f'http://127.0.0.1:{STREAMLIT_PORT}/{path}'
        
        # Copiar parámetros de query
        if request.query_string:
            target_url += f'?{request.query_string.decode()}'
        
        # Hacer petición a Streamlit
        if request.method == 'GET':
            resp = requests.get(target_url, headers=dict(request.headers), timeout=30)
        elif request.method == 'POST':
            resp = requests.post(target_url, 
                               data=request.get_data(),
                               headers=dict(request.headers),
                               timeout=30)
        else:
            resp = requests.request(request.method, target_url,
                                  data=request.get_data(),
                                  headers=dict(request.headers),
                                  timeout=30)
        
        # Retornar respuesta
        return Response(resp.content, 
                       status=resp.status_code,
                       headers=dict(resp.headers))
                       
    except requests.exceptions.RequestException as e:
        print(f"Proxy error: {e}")
        return f"Service temporarily unavailable. Error: {e}", 503

if __name__ == "__main__":
    print(f"Railway Proxy starting on port {RAILWAY_PORT}")
    print(f"Will proxy to Streamlit on port {STREAMLIT_PORT}")
    
    # Iniciar Streamlit en background
    streamlit_thread = Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    # Esperar a que Streamlit esté listo
    if wait_for_streamlit():
        print("✅ Streamlit is ready, starting proxy...")
    else:
        print("⚠️ Streamlit may not be ready, but starting proxy anyway...")
    
    # Iniciar servidor proxy
    app.run(host='0.0.0.0', port=RAILWAY_PORT, debug=False)