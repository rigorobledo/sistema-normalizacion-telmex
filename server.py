import subprocess
import os
from threading import Thread
import time
import requests

def run_streamlit():
    subprocess.run([
        "streamlit", "run", "app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ])

def health_check():
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    @app.route('/health')
    def health():
        try:
            response = requests.get('http://localhost:8501')
            if response.status_code == 200:
                return response.content, 200, {'Content-Type': 'text/html'}
        except:
            pass
        return "Service starting...", 202
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Iniciar Streamlit en background
    Thread(target=run_streamlit, daemon=True).start()
    time.sleep(5)  # Dar tiempo a que arranque
    # Iniciar proxy Flask
    health_check()