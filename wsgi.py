import os
import subprocess
import time
import requests
from threading import Thread
from flask import Flask, request, Response
import sys

app = Flask(__name__)

# Puerto donde correrá Streamlit
STREAMLIT_PORT = 8502

def start_streamlit():
    """Inicia Streamlit en segundo plano"""
    print(f"Starting Streamlit on port {STREAMLIT_PORT}")
    subprocess.run([
        sys.executable, '-m', 'streamlit', 'run', 'sistema_completo_normalizacion.py',
        f'--server.port={STREAMLIT_PORT}',
        '--server.address=127.0.0.1',
        '--server.headless=true',
        '--server.enableCORS=false',
        '--server.enableXsrfProtection=false',
        '--server.fileWatcherType=none'
    ])

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        response = requests.get(f'http://127.0.0.1:{STREAMLIT_PORT}', timeout=2)
        return {"status": "healthy", "streamlit": "running"}, 200
    except:
        return {"status": "unhealthy", "streamlit": "not ready"}, 503

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
        
        # Headers a mantener
        headers = {}
        for key, value in request.headers:
            if key.lower() not in ['host', 'content-length']:
                headers[key] = value
        
        # Hacer petición a Streamlit según el método
        if request.method == 'GET':
            resp = requests.get(target_url, headers=headers, timeout=30, stream=True)
        elif request.method == 'POST':
            resp = requests.post(target_url, 
                               data=request.get_data(),
                               headers=headers,
                               timeout=30, stream=True)
        else:
            resp = requests.request(request.method, target_url,
                                  data=request.get_data(),
                                  headers=headers,
                                  timeout=30, stream=True)
        
        # Filtrar headers de respuesta
        response_headers = {}
        for key, value in resp.headers.items():
            if key.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']:
                response_headers[key] = value
        
        # Retornar respuesta
        return Response(resp.content, 
                       status=resp.status_code,
                       headers=response_headers)
                       
    except requests.exceptions.RequestException as e:
        print(f"Proxy error: {e}")
        return f"<h1>Service Temporarily Unavailable</h1><p>Error: {e}</p>", 503

def wait_for_streamlit():
    """Espera a que Streamlit esté listo"""
    print("Waiting for Streamlit to be ready...")
    for i in range(60):  # Esperar hasta 2 minutos
        try:
            response = requests.get(f'http://127.0.0.1:{STREAMLIT_PORT}', timeout=2)
            if response.status_code == 200:
                print(f"✅ Streamlit is ready on port {STREAMLIT_PORT}")
                return True
        except:
            pass
        time.sleep(2)
    print("⚠️ Streamlit didn't start in time")
    return False

# Iniciar Streamlit cuando se importe este módulo
print("Initializing Streamlit...")
streamlit_thread = Thread(target=start_streamlit, daemon=True)
streamlit_thread.start()

# Dar tiempo para que Streamlit arranque
time.sleep(5)
wait_for_streamlit()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)