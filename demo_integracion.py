# ========================================
# ARCHIVO: demo_integracion.py
# DEMOSTRACIÓN DE INTEGRACIÓN COMPLETA
# ========================================

"""
💡 DEMOSTRACIÓN COMPLETA DEL ECOSISTEMA
Este script muestra cómo integrar todos los componentes:
- PostgreSQL como fuente de datos
- API REST para consultas
- Dashboard en tiempo real
- Reportes automáticos
- Integración con sistemas externos
"""

import requests
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime, timedelta
import subprocess
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor
import logging

# Configuración
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'normalizacion_domicilios',
    'user': 'postgres',
    'password': 'admin123'  # 🔑 Cambiar por tu contraseña
}

API_BASE_URL = "http://localhost:8000"
API_TOKEN = "demo-token-2025"

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# 1. CLASE PRINCIPAL DE DEMOSTRACIÓN
# ========================================

class DemoIntegracion:
    """Clase principal para demostrar la integración completa"""
    
    def __init__(self):
        self.engine = self._crear_conexion_db()
        self.api_headers = {"Authorization": f"Bearer {API_TOKEN}"}
        
    def _crear_conexion_db(self):
        """Crear conexión directa a PostgreSQL"""
        try:
            engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
            logger.info("✅ Conexión a PostgreSQL establecida")
            return engine
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return None
    
    def verificar_servicios(self):
        """Verificar que todos los servicios estén funcionando"""
        
        print("🔍 VERIFICANDO SERVICIOS...")
        print("=" * 50)
        
        servicios_estado = {}
        
        # 1. Verificar PostgreSQL
        try:
            if self.engine:
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM estados_normalizados"))
                    count = result.fetchone()[0]
                    servicios_estado['PostgreSQL'] = f"✅ Activo ({count:,} estados)"
            else:
                servicios_estado['PostgreSQL'] = "❌ No conectado"
        except Exception as e:
            servicios_estado['PostgreSQL'] = f"❌ Error: {str(e)[:50]}..."
        
        # 2. Verificar API REST
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                servicios_estado['API REST'] = "✅ Activa y respondiendo"
            else:
                servicios_estado['API REST'] = f"⚠️ Respondiendo con código {response.status_code}"
        except Exception as e:
            servicios_estado['API REST'] = "❌ No disponible (ejecuta: python api_normalizacion.py)"
        
        # 3. Verificar Dashboard
        try:
            # Intentar conectar al puerto típico de Streamlit
            response = requests.get("http://localhost:8501", timeout=5)
            servicios_estado['Dashboard'] = "✅ Activo" if response.status_code == 200 else "⚠️ Parcial"
        except:
            servicios_estado['Dashboard'] = "❌ No disponible (ejecuta: streamlit run dashboard_postgresql.py)"
        
        # 4. Verificar Sistema de Reportes
        import os
        if os.path.exists("reportes/automaticos/"):
            archivos_reportes = len([f for f in os.listdir("reportes/automaticos/") if f.endswith(('.html', '.xlsx'))])
            servicios_estado['Reportes'] = f"✅ Configurado ({archivos_reportes} reportes)"
        else:
            servicios_estado['Reportes'] = "⚠️ Carpeta no encontrada"
        
        # Mostrar resultados
        for servicio, estado in servicios_estado.items():
            print(f"   {servicio}: {estado}")
        
        print(f"\n📊 RESUMEN: {len([s for s in servicios_estado.values() if '✅' in s])}/4 servicios activos")
        
        return servicios_estado
    
    def demo_consultas_sql(self):
        """Demostrar consultas SQL directas a PostgreSQL"""
        
        print("\n🗄️ DEMO: CONSULTAS SQL DIRECTAS")
        print("=" * 50)
        
        if not self.engine:
            print("❌ No hay conexión a PostgreSQL")
            return
        
        consultas_demo = [
            {
                'nombre': 'Top 5 Estados con Mayor Confianza',
                'sql': """
                SELECT estado_normalizado, 
                       AVG(confianza) as confianza_promedio,
                       COUNT(*) as total_registros
                FROM estados_normalizados 
                WHERE confianza > 0
                GROUP BY estado_normalizado
                ORDER BY confianza_promedio DESC
                LIMIT 5
                """
            },
            {
                'nombre': 'Distribución de Métodos por División',
                'sql': """
                SELECT division, metodo_usado, COUNT(*) as cantidad
                FROM (
                    SELECT division, metodo_usado FROM estados_normalizados
                    UNION ALL
                    SELECT division, metodo_usado FROM municipios_normalizados
                    UNION ALL
                    SELECT division, metodo_usado FROM colonias_normalizadas
                ) todos_registros
                WHERE metodo_usado IS NOT NULL
                GROUP BY division, metodo_usado
                ORDER BY division, cantidad DESC
                """
            },
            {
                'nombre': 'Casos Críticos que Requieren Atención',
                'sql': """
                SELECT 'Estados' as tipo, texto_original, estado_normalizado as normalizado, confianza
                FROM estados_normalizados
                WHERE requiere_revision = true
                
                UNION ALL
                
                SELECT 'Municipios' as tipo, texto_original, municipio_normalizado as normalizado, confianza
                FROM municipios_normalizados
                WHERE requiere_revision = true
                
                ORDER BY confianza ASC
                LIMIT 10
                """
            }
        ]
        
        for consulta in consultas_demo:
            print(f"\n📋 {consulta['nombre']}:")
            print("-" * len(consulta['nombre']))
            
            try:
                df = pd.read_sql(text(consulta['sql']), self.engine)
                if not df.empty:
                    print(df.to_string(index=False))
                else:
                    print("   Sin resultados")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            time.sleep(1)  # Pausa para legibilidad
    
    def demo_api_rest(self):
        """Demostrar uso de la API REST"""
        
        print("\n🌐 DEMO: API REST")
        print("=" * 50)
        
        endpoints_demo = [
            {
                'nombre': 'Obtener Métricas Generales',
                'endpoint': '/api/v1/metricas',
                'metodo': 'GET'
            },
            {
                'nombre': 'Listar Estados (primeros 5)',
                'endpoint': '/api/v1/estados?por_pagina=5&pagina=1',
                'metodo': 'GET'
            },
            {
                'nombre': 'Buscar "CIUDAD DE MEXICO" en Estados',
                'endpoint': '/api/v1/buscar',
                'metodo': 'POST',
                'data': {
                    'texto_buscar': 'CIUDAD DE MEXICO',
                    'tipo_catalogo': 'estados',
                    'umbral_confianza': 0.8
                }
            },
            {
                'nombre': 'Estadísticas de Municipios',
                'endpoint': '/api/v1/estadisticas/municipios',
                'metodo': 'GET'
            }
        ]
        
        for demo in endpoints_demo:
            print(f"\n📡 {demo['nombre']}:")
            print(f"   {demo['metodo']} {API_BASE_URL}{demo['endpoint']}")
            
            try:
                if demo['metodo'] == 'GET':
                    response = requests.get(
                        f"{API_BASE_URL}{demo['endpoint']}", 
                        headers=self.api_headers,
                        timeout=10
                    )
                else:  # POST
                    response = requests.post(
                        f"{API_BASE_URL}{demo['endpoint']}", 
                        headers=self.api_headers,
                        json=demo['data'],
                        timeout=10
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Respuesta exitosa:")
                    
                    # Mostrar solo parte de la respuesta para legibilidad
                    if isinstance(data, dict):
                        if 'datos' in data and isinstance(data['datos'], list):
                            print(f"      Total registros: {data.get('total', 'N/A')}")
                            print(f"      Registros en respuesta: {len(data['datos'])}")
                        else:
                            # Mostrar primeras 3 claves del JSON
                            keys = list(data.keys())[:3]
                            for key in keys:
                                print(f"      {key}: {data[key]}")
                    else:
                        print(f"      Datos: {str(data)[:100]}...")
                
                else:
                    print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                    
            except Exception as e:
                print(f"   ❌ Error de conexión: {str(e)[:100]}...")
            
            time.sleep(1)
    
    def demo_integracion_externa(self):
        """Simular integración con sistema externo"""
        
        print("\n🔗 DEMO: INTEGRACIÓN CON SISTEMA EXTERNO")
        print("=" * 50)
        
        # Simular un sistema externo que consulta nuestros datos
        print("📋 Simulando sistema CRM consultando direcciones normalizadas...")
        
        # Casos de prueba realistas
        direcciones_consultar = [
            "DISTRITO FEDERAL",
            "EDO DE MEXICO", 
            "GUADALAJARA",
            "NEZA",
            "TIJUANA"
        ]
        
        for direccion in direcciones_consultar:
            print(f"\n🔍 CRM consulta: '{direccion}'")
            
            try:
                # Usar API para buscar normalización
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/buscar",
                    headers=self.api_headers,
                    json={
                        'texto_buscar': direccion,
                        'tipo_catalogo': 'estados',
                        'umbral_confianza': 0.7
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['resultados']:
                        resultado = data['resultados'][0]
                        print(f"   ✅ Normalizado: '{resultado.get('estado_normalizado', 'N/A')}'")
                        print(f"   📊 Confianza: {resultado.get('confianza', 0):.1%}")
                        print(f"   🔧 Método: {resultado.get('metodo_usado', 'N/A')}")
                    else:
                        print("   ⚠️ No se encontró normalización")
                else:
                    print(f"   ❌ Error API: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            
            time.sleep(0.5)
    
    def demo_reportes_automaticos(self):
        """Demostrar generación de reportes"""
        
        print("\n📊 DEMO: GENERACIÓN DE REPORTES")
        print("=" * 50)
        
        try:
            # Importar el generador de reportes
            from sistema_reportes import GeneradorReportes
            
            print("📋 Generando reporte de demostración...")
            
            generador = GeneradorReportes()
            
            # Generar reporte HTML
            archivo_html = generador.generar_reporte_html("demo")
            print(f"   ✅ Reporte HTML: {archivo_html}")
            
            # Generar reporte Excel  
            archivo_excel = generador.generar_reporte_excel("demo")
            print(f"   ✅ Reporte Excel: {archivo_excel}")
            
            print("\n📈 Contenido del reporte incluye:")
            print("   • Métricas generales del sistema")
            print("   • Análisis por catálogo (Estados, Municipios, Colonias)")
            print("   • Gráficos interactivos")
            print("   • Recomendaciones automáticas")
            print("   • Casos que requieren atención")
            
        except ImportError:
            print("⚠️ Módulo sistema_reportes no disponible")
            print("   Para activar: asegúrate de tener el archivo sistema_reportes.py")
        except Exception as e:
            print(f"❌ Error generando reportes: {e}")
    
    def demo_rendimiento(self):
        """Demostrar análisis de rendimiento"""
        
        print("\n⚡ DEMO: ANÁLISIS DE RENDIMIENTO")
        print("=" * 50)
        
        if not self.engine:
            print("❌ No hay conexión a PostgreSQL")
            return
        
        # Consultas de rendimiento
        consultas_rendimiento = [
            {
                'nombre': 'Conteo Total de Registros',
                'sql': """
                SELECT 
                    (SELECT COUNT(*) FROM estados_normalizados) as estados,
                    (SELECT COUNT(*) FROM municipios_normalizados) as municipios,
                    (SELECT COUNT(*) FROM colonias_normalizadas) as colonias
                """
            },
            {
                'nombre': 'Rendimiento por Método de Normalización',
                'sql': """
                SELECT metodo_usado,
                       COUNT(*) as cantidad,
                       AVG(confianza) as confianza_promedio,
                       COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as porcentaje
                FROM (
                    SELECT metodo_usado, confianza FROM estados_normalizados WHERE metodo_usado IS NOT NULL
                    UNION ALL
                    SELECT metodo_usado, confianza FROM municipios_normalizados WHERE metodo_usado IS NOT NULL
                    UNION ALL
                    SELECT metodo_usado, confianza FROM colonias_normalizadas WHERE metodo_usado IS NOT NULL
                ) todos_metodos
                GROUP BY metodo_usado
                ORDER BY cantidad DESC
                """
            }
        ]
        
        for consulta in consultas_rendimiento:
            print(f"\n📊 {consulta['nombre']}:")
            
            inicio = time.time()
            try:
                df = pd.read_sql(text(consulta['sql']), self.engine)
                tiempo_ejecucion = time.time() - inicio
                
                print(f"   ⏱️ Tiempo de ejecución: {tiempo_ejecucion:.3f} segundos")
                
                if not df.empty:
                    print(f"   📋 Resultados ({len(df)} filas):")
                    print(df.to_string(index=False, max_rows=5))
                    if len(df) > 5:
                        print("   ...")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    def ejecutar_demo_completo(self):
        """Ejecutar demostración completa"""
        
        print("🚀 DEMOSTRACIÓN COMPLETA DEL ECOSISTEMA DE NORMALIZACIÓN")
        print("=" * 80)
        print("Esta demo muestra la integración completa de todos los componentes:")
        print("• PostgreSQL como base de datos central")
        print("• API REST para consultas programáticas") 
        print("• Dashboard en tiempo real")
        print("• Sistema de reportes automáticos")
        print("• Integración con sistemas externos")
        print("=" * 80)
        
        # Verificar servicios
        servicios = self.verificar_servicios()
        
        input("\n📱 Presiona Enter para continuar con las demos...")
        
        # Demo de consultas SQL
        self.demo_consultas_sql()
        
        input("\n📱 Presiona Enter para continuar...")
        
        # Demo de API REST
        self.demo_api_rest()
        
        input("\n📱 Presiona Enter para continuar...")
        
        # Demo de integración externa
        self.demo_integracion_externa()
        
        input("\n📱 Presiona Enter para continuar...")
        
        # Demo de reportes
        self.demo_reportes_automaticos()
        
        input("\n📱 Presiona Enter para continuar...")
        
        # Demo de rendimiento
        self.demo_rendimiento()
        
        # Resumen final
        print("\n🎉 DEMOSTRACIÓN COMPLETADA")
        print("=" * 50)
        print("✅ Has visto cómo todos los componentes trabajan juntos:")
        print("   • Datos centralizados en PostgreSQL")
        print("   • API REST para acceso programático")
        print("   • Consultas SQL directas optimizadas") 
        print("   • Integración con sistemas externos")
        print("   • Reportes automáticos")
        print("   • Análisis de rendimiento en tiempo real")
        
        print("\n🚀 PRÓXIMOS PASOS SUGERIDOS:")
        print("   1. Integrar con tus sistemas reales de telecomunicaciones")
        print("   2. Configurar alertas automáticas")
        print("   3. Escalar a los 9 millones de registros reales")
        print("   4. Implementar backup y recuperación")
        print("   5. Configurar monitoreo de producción")

# ========================================
# 2. FUNCIONES DE UTILIDAD
# ========================================

def iniciar_servicios_demo():
    """Iniciar servicios necesarios para la demo (opcional)"""
    
    print("🚀 INICIANDO SERVICIOS PARA LA DEMO...")
    print("⚠️ Esta función intentará iniciar los servicios automáticamente")
    print("Si prefieres iniciarlos manualmente, presiona Ctrl+C")
    
    try:
        time.sleep(3)
        
        # Lista de comandos para iniciar servicios
        servicios = [
            {
                'nombre': 'API REST',
                'comando': 'python api_normalizacion.py',
                'puerto': 8000
            },
            {
                'nombre': 'Dashboard PostgreSQL', 
                'comando': 'streamlit run dashboard_postgresql.py --server.port 8501',
                'puerto': 8501
            }
        ]
        
        procesos = []
        
        for servicio in servicios:
            print(f"🔄 Iniciando {servicio['nombre']}...")
            try:
                # Iniciar proceso en background
                proceso = subprocess.Popen(
                    servicio['comando'].split(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                procesos.append((servicio['nombre'], proceso))
                print(f"   ✅ {servicio['nombre']} iniciado en puerto {servicio['puerto']}")
                time.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error iniciando {servicio['nombre']}: {e}")
        
        if procesos:
            print(f"\n✅ {len(procesos)} servicios iniciados correctamente")
            print("⚠️ Los servicios seguirán ejecutándose en background")
            print("💡 Para detenerlos, usa Ctrl+C o cierra la terminal")
            
            return procesos
        
    except KeyboardInterrupt:
        print("\n👋 Inicio automático cancelado por el usuario")
        return []
    
    return []

def mostrar_urls_servicios():
    """Mostrar URLs de los servicios disponibles"""
    
    print("\n🌐 URLS DE SERVICIOS DISPONIBLES:")
    print("=" * 50)
    
    servicios_urls = [
        ("API REST - Documentación", "http://localhost:8000/docs"),
        ("API REST - Health Check", "http://localhost:8000/health"),
        ("Dashboard PostgreSQL", "http://localhost:8501"),
        ("Dashboard Original", "http://localhost:8502")
    ]
    
    for nombre, url in servicios_urls:
        print(f"📡 {nombre}:")
        print(f"   {url}")
        
        # Verificar si está disponible
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("   ✅ Disponible")
            else:
                print(f"   ⚠️ Responde con código {response.status_code}")
        except:
            print("   ❌ No disponible")
        
        print()

# ========================================
# 3. FUNCIÓN PRINCIPAL
# ========================================

def main():
    """Función principal del demo"""
    
    print("🎯 DEMO DE INTEGRACIÓN COMPLETA")
    print("Sistema de Normalización de Domicilios")
    print("=" * 50)
    
    # Mostrar menú de opciones
    print("Opciones disponibles:")
    print("1. 🚀 Ejecutar demo completo")
    print("2. 🔍 Solo verificar servicios")
    print("3. 🗄️ Solo demo de PostgreSQL")
    print("4. 🌐 Solo demo de API REST")
    print("5. 📊 Solo demo de reportes")
    print("6. 🌐 Mostrar URLs de servicios")
    print("7. 🚀 Iniciar servicios automáticamente")
    print("8. 🌐 Abrir servicios en navegador")
    print("9. ❌ Salir")
    
    while True:
        try:
            opcion = input("\nSelecciona una opción (1-9): ").strip()
            
            demo = DemoIntegracion()
            
            if opcion == "1":
                demo.ejecutar_demo_completo()
                break
            
            elif opcion == "2":
                demo.verificar_servicios()
            
            elif opcion == "3":
                demo.demo_consultas_sql()
                demo.demo_rendimiento()
            
            elif opcion == "4":
                demo.demo_api_rest()
            
            elif opcion == "5":
                demo.demo_reportes_automaticos()
            
            elif opcion == "6":
                mostrar_urls_servicios()
            
            elif opcion == "7":
                iniciar_servicios_demo()
            
            elif opcion == "8":
                urls = [
                    "http://localhost:8000/docs",
                    "http://localhost:8501"
                ]
                for url in urls:
                    print(f"🌐 Abriendo: {url}")
                    webbrowser.open(url)
                    time.sleep(1)
            
            elif opcion == "9":
                print("👋 ¡Hasta luego!")
                break
            
            else:
                print("❌ Opción no válida. Selecciona 1-9.")
        
        except KeyboardInterrupt:
            print("\n👋 Demo interrumpido por el usuario")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()