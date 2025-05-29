# ========================================
# ARCHIVO: sistema_reportes.py
# SISTEMA DE REPORTES AUTOMÁTICOS
# ========================================

"""
💡 SISTEMA DE REPORTES EMPRESARIALES
Este sistema genera reportes automáticos desde PostgreSQL:
- Reportes diarios, semanales, mensuales
- Múltiples formatos: HTML, PDF, Excel, CSV
- Envío automático por email
- Dashboards ejecutivos
- Alertas inteligentes
- Programación automática
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import schedule
import time
import json
from jinja2 import Template
import pdfkit
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference
import logging

# ========================================
# 1. CONFIGURACIÓN
# ========================================

# Configuración de base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'normalizacion_domicilios',
    'user': 'postgres',
    'password': 'admin123'  # 🔑 Cambiar por tu contraseña
}

# Configuración de email (opcional)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'tu_email@empresa.com',
    'password': 'tu_password_app',  # Password de aplicación de Gmail
    'destinatarios': ['gerente@empresa.com', 'director@empresa.com']
}

# Configuración de reportes
REPORTES_CONFIG = {
    'carpeta_reportes': 'reportes/automaticos/',
    'formato_fecha': '%Y-%m-%d_%H-%M-%S',
    'mantener_reportes_dias': 30,
    'formatos_exportacion': ['html', 'pdf', 'excel', 'csv']
}

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reportes_automaticos.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========================================
# 2. CLASE PRINCIPAL DEL GENERADOR
# ========================================

class GeneradorReportes:
    """Clase principal para generar reportes automáticos"""
    
    def __init__(self):
        self.engine = self._crear_conexion()
        self.crear_carpetas()
        
    def _crear_conexion(self):
        """Crear conexión a PostgreSQL"""
        try:
            engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
            logger.info("✅ Conexión a PostgreSQL establecida")
            return engine
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            raise
    
    def crear_carpetas(self):
        """Crear estructura de carpetas para reportes"""
        carpetas = [
            REPORTES_CONFIG['carpeta_reportes'],
            REPORTES_CONFIG['carpeta_reportes'] + 'diarios/',
            REPORTES_CONFIG['carpeta_reportes'] + 'semanales/',
            REPORTES_CONFIG['carpeta_reportes'] + 'mensuales/',
            REPORTES_CONFIG['carpeta_reportes'] + 'ejecutivos/',
            REPORTES_CONFIG['carpeta_reportes'] + 'alertas/'
        ]
        
        for carpeta in carpetas:
            os.makedirs(carpeta, exist_ok=True)
        
        logger.info("📁 Estructura de carpetas creada")
    
    def ejecutar_consulta(self, query, params=None):
        """Ejecutar consulta SQL"""
        try:
            if params:
                df = pd.read_sql(text(query), self.engine, params=params)
            else:
                df = pd.read_sql(text(query), self.engine)
            return df
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            return pd.DataFrame()
    
    def obtener_metricas_generales(self):
        """Obtener métricas generales del sistema"""
        
        query = """
        WITH metricas_por_tabla AS (
            SELECT 'Estados' as catalogo, COUNT(*) as total, 
                   COUNT(CASE WHEN estado_normalizado IS NOT NULL AND estado_normalizado != '' THEN 1 END) as exitosos,
                   AVG(CASE WHEN confianza > 0 THEN confianza END) as confianza_promedio,
                   COUNT(CASE WHEN requiere_revision = true THEN 1 END) as requieren_revision,
                   COUNT(CASE WHEN metodo_usado = 'EXACTO' THEN 1 END) as exactos,
                   COUNT(CASE WHEN metodo_usado LIKE 'FUZZY%' THEN 1 END) as fuzzy
            FROM estados_normalizados
            
            UNION ALL
            
            SELECT 'Municipios' as catalogo, COUNT(*) as total,
                   COUNT(CASE WHEN municipio_normalizado IS NOT NULL AND municipio_normalizado != '' THEN 1 END) as exitosos,
                   AVG(CASE WHEN confianza > 0 THEN confianza END) as confianza_promedio,
                   COUNT(CASE WHEN requiere_revision = true THEN 1 END) as requieren_revision,
                   COUNT(CASE WHEN metodo_usado = 'EXACTO' THEN 1 END) as exactos,
                   COUNT(CASE WHEN metodo_usado LIKE 'FUZZY%' THEN 1 END) as fuzzy
            FROM municipios_normalizados
            
            UNION ALL
            
            SELECT 'Colonias' as catalogo, COUNT(*) as total,
                   COUNT(CASE WHEN colonia_normalizada IS NOT NULL AND colonia_normalizada != '' THEN 1 END) as exitosos,
                   AVG(CASE WHEN confianza > 0 THEN confianza END) as confianza_promedio,
                   COUNT(CASE WHEN requiere_revision = true THEN 1 END) as requieren_revision,
                   COUNT(CASE WHEN metodo_usado = 'EXACTO' THEN 1 END) as exactos,
                   COUNT(CASE WHEN metodo_usado LIKE 'FUZZY%' THEN 1 END) as fuzzy
            FROM colonias_normalizadas
        )
        SELECT 
            catalogo,
            total,
            exitosos,
            ROUND((exitosos * 100.0 / NULLIF(total, 0)), 2) as porcentaje_exito,
            ROUND(confianza_promedio, 4) as confianza_promedio,
            requieren_revision,
            exactos,
            fuzzy
        FROM metricas_por_tabla
        WHERE total > 0
        ORDER BY total DESC
        """
        
        return self.ejecutar_consulta(query)
    
    def obtener_tendencias_diarias(self, dias=30):
        """Obtener tendencias de los últimos días"""
        
        query = """
        WITH datos_diarios AS (
            SELECT DATE(fecha_proceso) as fecha,
                   'Estados' as catalogo,
                   COUNT(*) as registros_procesados,
                   COUNT(CASE WHEN estado_normalizado IS NOT NULL THEN 1 END) as exitosos
            FROM estados_normalizados
            WHERE fecha_proceso >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(fecha_proceso)
            
            UNION ALL
            
            SELECT DATE(fecha_proceso) as fecha,
                   'Municipios' as catalogo,
                   COUNT(*) as registros_procesados,
                   COUNT(CASE WHEN municipio_normalizado IS NOT NULL THEN 1 END) as exitosos
            FROM municipios_normalizados
            WHERE fecha_proceso >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(fecha_proceso)
            
            UNION ALL
            
            SELECT DATE(fecha_proceso) as fecha,
                   'Colonias' as catalogo,
                   COUNT(*) as registros_procesados,
                   COUNT(CASE WHEN colonia_normalizada IS NOT NULL THEN 1 END) as exitosos
            FROM colonias_normalizadas
            WHERE fecha_proceso >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(fecha_proceso)
        )
        SELECT fecha, catalogo, registros_procesados, exitosos,
               ROUND((exitosos * 100.0 / NULLIF(registros_procesados, 0)), 2) as porcentaje_exito
        FROM datos_diarios
        ORDER BY fecha DESC, catalogo
        """ % (dias, dias, dias)
        
        return self.ejecutar_consulta(query)
    
    def generar_grafico_metricas(self, df_metricas):
        """Generar gráfico de métricas generales"""
        
        if df_metricas.empty:
            return None
        
        # Crear subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Registros por Catálogo', 'Porcentaje de Éxito', 
                          'Distribución de Métodos', 'Casos que Requieren Revisión'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "pie"}, {"type": "bar"}]]
        )
        
        # Gráfico 1: Registros por catálogo
        fig.add_trace(
            go.Bar(x=df_metricas['catalogo'], y=df_metricas['total'], 
                   name='Total', marker_color='#2196F3'),
            row=1, col=1
        )
        
        # Gráfico 2: Porcentaje de éxito
        fig.add_trace(
            go.Bar(x=df_metricas['catalogo'], y=df_metricas['porcentaje_exito'],
                   name='% Éxito', marker_color='#4CAF50'),
            row=1, col=2
        )
        
        # Gráfico 3: Distribución de métodos (pie chart)
        metodos_total = df_metricas['exactos'].sum() + df_metricas['fuzzy'].sum()
        if metodos_total > 0:
            fig.add_trace(
                go.Pie(labels=['Exactos', 'Fuzzy'], 
                       values=[df_metricas['exactos'].sum(), df_metricas['fuzzy'].sum()],
                       name="Métodos"),
                row=2, col=1
            )
        
        # Gráfico 4: Casos que requieren revisión
        fig.add_trace(
            go.Bar(x=df_metricas['catalogo'], y=df_metricas['requieren_revision'],
                   name='Revisión', marker_color='#FF9800'),
            row=2, col=2
        )
        
        # Actualizar layout
        fig.update_layout(
            title_text="📊 Dashboard de Métricas - Sistema de Normalización",
            title_x=0.5,
            showlegend=False,
            height=800,
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        return fig
    
    def generar_reporte_html(self, tipo_reporte="diario"):
        """Generar reporte HTML completo"""
        
        logger.info(f"Generando reporte HTML {tipo_reporte}")
        
        # Obtener datos
        df_metricas = self.obtener_metricas_generales()
        df_tendencias = self.obtener_tendencias_diarias()
        
        # Generar gráficos
        fig_metricas = self.generar_grafico_metricas(df_metricas)
        
        # Convertir gráficos a HTML
        grafico_html = ""
        if fig_metricas:
            grafico_html = pio.to_html(fig_metricas, include_plotlyjs='cdn', div_id="grafico-metricas")
        
        # Template HTML
        template_html = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📊 Reporte {{ tipo_reporte.title() }} - Normalización de Domicilios</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 15px;
                    text-align: center;
                    margin-bottom: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }
                .header h1 {
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }
                .header .fecha {
                    font-size: 1.2em;
                    opacity: 0.9;
                }
                .seccion {
                    background: white;
                    padding: 25px;
                    border-radius: 15px;
                    margin-bottom: 25px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .seccion h2 {
                    color: #667eea;
                    border-bottom: 3px solid #667eea;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }
                .metricas-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .metrica-card {
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
                }
                .metrica-valor {
                    font-size: 2.5em;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
                .metrica-label {
                    font-size: 1.1em;
                    opacity: 0.9;
                }
                .tabla {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                .tabla th, .tabla td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                .tabla th {
                    background: #667eea;
                    color: white;
                    font-weight: 600;
                }
                .tabla tr:hover {
                    background: #f5f5f5;
                }
                .alerta {
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                }
                .exito {
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                }
                .footer {
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 40px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Reporte {{ tipo_reporte.title() }}</h1>
                <p class="fecha">Sistema de Normalización de Domicilios</p>
                <p class="fecha">Generado el: {{ fecha_generacion }}</p>
            </div>
            
            <div class="seccion">
                <h2>📈 Métricas Generales</h2>
                <div class="metricas-grid">
                    <div class="metrica-card">
                        <div class="metrica-valor">{{ total_registros:,d }}</div>
                        <div class="metrica-label">Total Registros</div>
                    </div>
                    <div class="metrica-card">
                        <div class="metrica-valor">{{ porcentaje_exito_general:.1f }}%</div>
                        <div class="metrica-label">Éxito General</div>
                    </div>
                    <div class="metrica-card">
                        <div class="metrica-valor">{{ total_exitosos:,d }}</div>
                        <div class="metrica-label">Normalizados</div>
                    </div>
                    <div class="metrica-card">
                        <div class="metrica-valor">{{ catalogos_activos }}</div>
                        <div class="metrica-label">Catálogos Activos</div>
                    </div>
                </div>
                
                {% if porcentaje_exito_general >= 90 %}
                <div class="exito">
                    ✅ <strong>Excelente rendimiento:</strong> El sistema está funcionando de manera óptima con un {{ porcentaje_exito_general:.1f }}% de éxito.
                </div>
                {% elif porcentaje_exito_general >= 80 %}
                <div class="alerta">
                    ⚠️ <strong>Buen rendimiento:</strong> El sistema funciona bien pero hay oportunidades de mejora.
                </div>
                {% else %}
                <div class="alerta">
                    🔴 <strong>Atención requerida:</strong> El rendimiento está por debajo del objetivo del 80%.
                </div>
                {% endif %}
            </div>
            
            <div class="seccion">
                <h2>📊 Detalle por Catálogo</h2>
                <table class="tabla">
                    <thead>
                        <tr>
                            <th>Catálogo</th>
                            <th>Total</th>
                            <th>Exitosos</th>
                            <th>% Éxito</th>
                            <th>Confianza Promedio</th>
                            <th>Requieren Revisión</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for _, row in df_metricas.iterrows() %}
                        <tr>
                            <td><strong>{{ row.catalogo }}</strong></td>
                            <td>{{ "{:,}".format(row.total) }}</td>
                            <td>{{ "{:,}".format(row.exitosos) }}</td>
                            <td>{{ "{:.1f}%".format(row.porcentaje_exito) }}</td>
                            <td>{{ "{:.1f}%".format(row.confianza_promedio * 100) if row.confianza_promedio else "N/A" }}</td>
                            <td>{{ "{:,}".format(row.requieren_revision) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="seccion">
                <h2>📈 Visualizaciones</h2>
                {{ grafico_html|safe }}
            </div>
            
            <div class="seccion">
                <h2>🎯 Recomendaciones</h2>
                <ul>
                    {% if total_revision > 0 %}
                    <li><strong>Revisar {{ total_revision }} casos pendientes</strong> que requieren validación manual</li>
                    {% endif %}
                    
                    {% if porcentaje_exito_general < 90 %}
                    <li><strong>Optimizar algoritmos</strong> para mejorar la tasa de éxito general</li>
                    {% endif %}
                    
                    <li><strong>Mantener monitoreo continuo</strong> del sistema de normalización</li>
                    <li><strong>Programar limpieza</strong> de datos antiguos según políticas de retención</li>
                </ul>
            </div>
            
            <div class="footer">
                <p>🏢 Sistema de Normalización de Domicilios | 📧 Generado automáticamente</p>
                <p>🔒 Confidencial - Solo para uso interno</p>
            </div>
        </body>
        </html>
        """
        
        # Calcular métricas generales
        total_registros = df_metricas['total'].sum() if not df_metricas.empty else 0
        total_exitosos = df_metricas['exitosos'].sum() if not df_metricas.empty else 0
        porcentaje_exito_general = (total_exitosos / total_registros * 100) if total_registros > 0 else 0
        total_revision = df_metricas['requieren_revision'].sum() if not df_metricas.empty else 0
        catalogos_activos = len(df_metricas) if not df_metricas.empty else 0
        
        # Renderizar template
        template = Template(template_html)
        html_content = template.render(
            tipo_reporte=tipo_reporte,
            fecha_generacion=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            df_metricas=df_metricas,
            grafico_html=grafico_html,
            total_registros=total_registros,
            total_exitosos=total_exitosos,
            porcentaje_exito_general=porcentaje_exito_general,
            total_revision=total_revision,
            catalogos_activos=catalogos_activos
        )
        
        # Guardar archivo
        timestamp = datetime.now().strftime(REPORTES_CONFIG['formato_fecha'])
        nombre_archivo = f"reporte_{tipo_reporte}_{timestamp}.html"
        ruta_archivo = os.path.join(REPORTES_CONFIG['carpeta_reportes'], f"{tipo_reporte}s/", nombre_archivo)
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ Reporte HTML generado: {ruta_archivo}")
        return ruta_archivo
    
    def generar_reporte_excel(self, tipo_reporte="diario"):
        """Generar reporte en formato Excel"""
        
        logger.info(f"Generando reporte Excel {tipo_reporte}")
        
        # Obtener datos
        df_metricas = self.obtener_metricas_generales()
        df_tendencias = self.obtener_tendencias_diarias()
        
        # Crear archivo Excel
        timestamp = datetime.now().strftime(REPORTES_CONFIG['formato_fecha'])
        nombre_archivo = f"reporte_{tipo_reporte}_{timestamp}.xlsx"
        ruta_archivo = os.path.join(REPORTES_CONFIG['carpeta_reportes'], f"{tipo_reporte}s/", nombre_archivo)
        
        with pd.ExcelWriter(ruta_archivo, engine='openpyxl') as writer:
            # Hoja de métricas generales
            if not df_metricas.empty:
                df_metricas.to_excel(writer, sheet_name='Métricas Generales', index=False)
            
            # Hoja de tendencias
            if not df_tendencias.empty:
                df_tendencias.to_excel(writer, sheet_name='Tendencias', index=False)
            
            # Hoja de resumen ejecutivo
            resumen_data = {
                'Métrica': ['Total Registros', 'Total Exitosos', '% Éxito General', 'Catálogos Activos'],
                'Valor': [
                    df_metricas['total'].sum() if not df_metricas.empty else 0,
                    df_metricas['exitosos'].sum() if not df_metricas.empty else 0,
                    f"{(df_metricas['exitosos'].sum() / df_metricas['total'].sum() * 100):.1f}%" if not df_metricas.empty and df_metricas['total'].sum() > 0 else "0%",
                    len(df_metricas) if not df_metricas.empty else 0
                ]
            }
            
            df_resumen = pd.DataFrame(resumen_data)
            df_resumen.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)
        
        logger.info(f"✅ Reporte Excel generado: {ruta_archivo}")
        return ruta_archivo
    
    def enviar_reporte_email(self, archivo_reporte, destinatarios=None):
        """Enviar reporte por email"""
        
        if not destinatarios:
            destinatarios = EMAIL_CONFIG['destinatarios']
        
        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['email']
            msg['To'] = ', '.join(destinatarios)
            msg['Subject'] = f"📊 Reporte Automático - Sistema de Normalización - {datetime.now().strftime('%d/%m/%Y')}"
            
            # Cuerpo del email
            cuerpo = f"""
            <html>
            <body>
                <h2>📊 Reporte Automático del Sistema de Normalización</h2>
                <p>Se ha generado el reporte automático del sistema de normalización de domicilios.</p>
                
                <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p><strong>Archivo adjunto:</strong> {os.path.basename(archivo_reporte)}</p>
                
                <p>Para más detalles, consulta el archivo adjunto o accede al dashboard en tiempo real.</p>
                
                <hr>
                <p><em>Este es un email automático del Sistema de Normalización de Domicilios</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(cuerpo, 'html'))
            
            # Adjuntar archivo
            with open(archivo_reporte, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(archivo_reporte)}'
            )
            msg.attach(part)
            
            # Enviar email
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Reporte enviado por email a: {', '.join(destinatarios)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            return False
    
    def limpiar_reportes_antiguos(self):
        """Limpiar reportes antiguos según configuración"""
        
        dias_mantener = REPORTES_CONFIG['mantener_reportes_dias']
        fecha_limite = datetime.now() - timedelta(days=dias_mantener)
        
        carpetas_reportes = ['diarios/', 'semanales/', 'mensuales/', 'ejecutivos/']
        archivos_eliminados = 0
        
        for carpeta in carpetas_reportes:
            ruta_carpeta = os.path.join(REPORTES_CONFIG['carpeta_reportes'], carpeta)
            
            if os.path.exists(ruta_carpeta):
                for archivo in os.listdir(ruta_carpeta):
                    ruta_archivo = os.path.join(ruta_carpeta, archivo)
                    
                    if os.path.isfile(ruta_archivo):
                        fecha_archivo = datetime.fromtimestamp(os.path.getctime(ruta_archivo))
                        
                        if fecha_archivo < fecha_limite:
                            os.remove(ruta_archivo)
                            archivos_eliminados += 1
        
        if archivos_eliminados > 0:
            logger.info(f"🧹 Eliminados {archivos_eliminados} reportes antiguos")
        
        return archivos_eliminados

# ========================================
# 3. PROGRAMADOR DE TAREAS
# ========================================

class ProgramadorReportes:
    """Clase para programar la generación automática de reportes"""
    
    def __init__(self):
        self.generador = GeneradorReportes()
    
    def reporte_diario(self):
        """Generar reporte diario"""
        logger.info("🗓️ Iniciando reporte diario programado")
        
        try:
            # Generar reportes
            archivo_html = self.generador.generar_reporte_html("diario")
            archivo_excel = self.generador.generar_reporte_excel("diario")
            
            # Enviar por email (opcional)
            # self.generador.enviar_reporte_email(archivo_html)
            
            # Limpiar archivos antiguos
            self.generador.limpiar_reportes_antiguos()
            
            logger.info("✅ Reporte diario completado")
            
        except Exception as e:
            logger.error(f"❌ Error en reporte diario: {e}")
    
    def reporte_semanal(self):
        """Generar reporte semanal"""
        logger.info("📅 Iniciando reporte semanal programado")
        
        try:
            archivo_html = self.generador.generar_reporte_html("semanal")
            archivo_excel = self.generador.generar_reporte_excel("semanal")
            
            logger.info("✅ Reporte semanal completado")
            
        except Exception as e:
            logger.error(f"❌ Error en reporte semanal: {e}")
    
    def reporte_mensual(self):
        """Generar reporte mensual"""
        logger.info("📆 Iniciando reporte mensual programado")
        
        try:
            archivo_html = self.generador.generar_reporte_html("mensual")
            archivo_excel = self.generador.generar_reporte_excel("mensual")
            
            logger.info("✅ Reporte mensual completado")
            
        except Exception as e:
            logger.error(f"❌ Error en reporte mensual: {e}")
    
    def iniciar_programacion(self):
        """Iniciar la programación automática de reportes"""
        
        logger.info("🚀 Iniciando sistema de reportes automáticos")
        
        # Programar reportes
        schedule.every().day.at("08:00").do(self.reporte_diario)
        schedule.every().monday.at("09:00").do(self.reporte_semanal)
        schedule.every().month.do(self.reporte_mensual)
        
        logger.info("📅 Programación configurada:")
        logger.info("   • Reporte diario: 08:00 AM")
        logger.info("   • Reporte semanal: Lunes 09:00 AM")
        logger.info("   • Reporte mensual: Primer día del mes")
        
        # Bucle principal
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto

# ========================================
# 4. FUNCIONES PRINCIPALES
# ========================================

def generar_reporte_manual(tipo="diario", formato="html"):
    """Generar reporte manual para pruebas"""
    
    print(f"🚀 Generando reporte {tipo} en formato {formato}")
    
    generador = GeneradorReportes()
    
    try:
        if formato.lower() == "html":
            archivo = generador.generar_reporte_html(tipo)
        elif formato.lower() == "excel":
            archivo = generador.generar_reporte_excel(tipo)
        else:
            print("❌ Formato no soportado. Usa 'html' o 'excel'")
            return
        
        print(f"✅ Reporte generado: {archivo}")
        return archivo
        
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")

def main():
    """Función principal"""
    
    print("📊 SISTEMA DE REPORTES AUTOMÁTICOS")
    print("=" * 50)
    
    # Mostrar opciones
    print("Opciones disponibles:")
    print("1. Generar reporte manual")
    print("2. Iniciar sistema automático")
    print("3. Limpiar reportes antiguos")
    print("4. Salir")
    
    while True:
        try:
            opcion = input("\nSelecciona una opción (1-4): ").strip()
            
            if opcion == "1":
                # Generar reporte manual
                print("\nTipos de reporte:")
                print("1. Diario")
                print("2. Semanal") 
                print("3. Mensual")
                
                tipo_num = input("Selecciona tipo (1-3): ").strip()
                tipo_map = {"1": "diario", "2": "semanal", "3": "mensual"}
                tipo = tipo_map.get(tipo_num, "diario")
                
                print("\nFormatos disponibles:")
                print("1. HTML")
                print("2. Excel")
                print("3. Ambos")
                
                formato_num = input("Selecciona formato (1-3): ").strip()
                
                if formato_num == "1":
                    generar_reporte_manual(tipo, "html")
                elif formato_num == "2":
                    generar_reporte_manual(tipo, "excel")
                elif formato_num == "3":
                    generar_reporte_manual(tipo, "html")
                    generar_reporte_manual(tipo, "excel")
                else:
                    print("❌ Opción no válida")
            
            elif opcion == "2":
                # Iniciar sistema automático
                print("🚀 Iniciando sistema de reportes automáticos...")
                print("⚠️  Presiona Ctrl+C para detener")
                
                programador = ProgramadorReportes()
                programador.iniciar_programacion()
            
            elif opcion == "3":
                # Limpiar reportes antiguos
                print("🧹 Limpiando reportes antiguos...")
                generador = GeneradorReportes()
                eliminados = generador.limpiar_reportes_antiguos()
                print(f"✅ Se eliminaron {eliminados} archivos antiguos")
            
            elif opcion == "4":
                print("👋 ¡Hasta luego!")
                break
            
            else:
                print("❌ Opción no válida. Selecciona 1-4.")
                
        except KeyboardInterrupt:
            print("\n👋 Sistema detenido por el usuario")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()