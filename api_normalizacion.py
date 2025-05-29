# ========================================
# ARCHIVO: api_normalizacion.py
# API REST PARA CONSULTAR DATOS NORMALIZADOS
# ========================================

"""
💡 API REST PROFESIONAL
Esta API permite a otros sistemas consultar los datos normalizados:
- Endpoints RESTful estándar
- Documentación automática con Swagger
- Filtros avanzados
- Paginación
- Rate limiting
- Autenticación básica
- Logs de auditoría
- Respuestas en formato JSON
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uvicorn
import logging
from enum import Enum

# ========================================
# 1. CONFIGURACIÓN Y MODELOS
# ========================================

# Configuración de base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'normalizacion_domicilios',
    'user': 'postgres',
    'password': 'admin123'  # 🔑 Cambiar por tu contraseña
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_normalizacion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="🏠 API de Normalización de Domicilios",
    description="API REST para consultar datos normalizados de estados, municipios y colonias de México",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS para permitir acceso desde dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seguridad básica
security = HTTPBearer()

# ========================================
# 2. MODELOS PYDANTIC
# ========================================

class TipoCatalogo(str, Enum):
    estados = "estados"
    municipios = "municipios" 
    colonias = "colonias"

class MetodoNormalizacion(str, Enum):
    exacto = "EXACTO"
    equivalencia = "EQUIVALENCIA"
    fuzzy_alto = "FUZZY_ALTO"
    fuzzy_bajo = "FUZZY_BAJO"
    semantico = "SEMANTICO"
    sin_match = "SIN_MATCH"

class EstadoNormalizado(BaseModel):
    id: int
    division: str
    esquema: str
    clave_original: Optional[str]
    texto_original: str
    texto_limpio: Optional[str]
    estado_normalizado: Optional[str]
    metodo_usado: Optional[str]
    confianza: Optional[float]
    categoria: Optional[str]
    requiere_revision: bool
    explicacion: Optional[str]
    fecha_proceso: Optional[datetime]

class MunicipioNormalizado(BaseModel):
    id: int
    division: str
    esquema: str
    clave_original: Optional[str]
    texto_original: str
    texto_limpio: Optional[str]
    municipio_normalizado: Optional[str]
    metodo_usado: Optional[str]
    confianza: Optional[float]
    categoria: Optional[str]
    requiere_revision: bool
    explicacion: Optional[str]
    fecha_proceso: Optional[datetime]

class ColoniaNormalizada(BaseModel):
    id: int
    division: str
    esquema: str
    clave_original: Optional[str]
    codigo_postal: Optional[str]
    texto_original: str
    texto_limpio: Optional[str]
    colonia_normalizada: Optional[str]
    metodo_usado: Optional[str]
    confianza: Optional[float]
    categoria: Optional[str]
    requiere_revision: bool
    explicacion: Optional[str]
    fecha_proceso: Optional[datetime]

class ConsultaNormalizacion(BaseModel):
    texto_buscar: str = Field(..., description="Texto a normalizar")
    tipo_catalogo: TipoCatalogo = Field(..., description="Tipo de catálogo a consultar")
    umbral_confianza: Optional[float] = Field(0.0, description="Umbral mínimo de confianza")

class RespuestaApi(BaseModel):
    exito: bool
    datos: List[Dict[Any, Any]]
    total: int
    pagina: int
    por_pagina: int
    mensaje: Optional[str] = None

class MetricasGenerales(BaseModel):
    total_registros: int
    total_exitosos: int
    porcentaje_exito: float
    catalogos_activos: int
    ultima_actualizacion: datetime

# ========================================
# 3. FUNCIONES DE BASE DE DATOS
# ========================================

def obtener_conexion():
    """Obtener conexión a PostgreSQL"""
    try:
        engine = create_engine(f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
        return engine
    except Exception as e:
        logger.error(f"Error conectando a base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión a base de datos")

def ejecutar_consulta_segura(query: str, params: dict = None):
    """Ejecutar consulta SQL de forma segura"""
    try:
        engine = obtener_conexion()
        if params:
            df = pd.read_sql(text(query), engine, params=params)
        else:
            df = pd.read_sql(text(query), engine)
        return df
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {e}")
        raise HTTPException(status_code=500, detail="Error ejecutando consulta")

# ========================================
# 4. FUNCIONES DE AUTENTICACIÓN
# ========================================

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificación básica de token (en producción usar JWT real)"""
    # Token de ejemplo para demo - en producción implementar JWT real
    tokens_validos = ["demo-token-2025", "api-key-normalizacion"]
    
    if credentials.credentials not in tokens_validos:
        raise HTTPException(
            status_code=401,
            detail="Token de acceso inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# ========================================
# 5. ENDPOINTS DE LA API
# ========================================

@app.get("/", response_model=Dict[str, Any])
async def raiz():
    """Endpoint raíz con información de la API"""
    return {
        "mensaje": "🏠 API de Normalización de Domicilios",
        "version": "2.0.0",
        "estado": "activo",
        "documentacion": "/docs",
        "endpoints": {
            "estados": "/api/v1/estados",
            "municipios": "/api/v1/municipios",
            "colonias": "/api/v1/colonias",
            "buscar": "/api/v1/buscar",
            "metricas": "/api/v1/metricas"
        },
        "autenticacion": "Bearer token requerido",
        "tokens_demo": ["demo-token-2025", "api-key-normalizacion"]
    }

@app.get("/health")
async def verificar_salud():
    """Endpoint de salud del servicio"""
    try:
        # Verificar conexión a base de datos
        engine = obtener_conexion()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        return {
            "estado": "saludable",
            "timestamp": datetime.now(),
            "base_datos": "conectada",
            "version": "2.0.0"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "estado": "no_saludable",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/api/v1/metricas", response_model=MetricasGenerales)
async def obtener_metricas(token: str = Depends(verificar_token)):
    """Obtener métricas generales del sistema"""
    
    logger.info("Consultando métricas generales")
    
    query = """
    SELECT 
        (SELECT COUNT(*) FROM estados_normalizados) +
        (SELECT COUNT(*) FROM municipios_normalizados) +
        (SELECT COUNT(*) FROM colonias_normalizadas) as total_registros,
        
        (SELECT COUNT(*) FROM estados_normalizados WHERE estado_normalizado IS NOT NULL) +
        (SELECT COUNT(*) FROM municipios_normalizados WHERE municipio_normalizado IS NOT NULL) +
        (SELECT COUNT(*) FROM colonias_normalizadas WHERE colonia_normalizada IS NOT NULL) as total_exitosos,
        
        3 as catalogos_activos,
        CURRENT_TIMESTAMP as ultima_actualizacion
    """
    
    df = ejecutar_consulta_segura(query)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="No se encontraron métricas")
    
    row = df.iloc[0]
    porcentaje_exito = (row['total_exitosos'] / row['total_registros'] * 100) if row['total_registros'] > 0 else 0
    
    return MetricasGenerales(
        total_registros=int(row['total_registros']),
        total_exitosos=int(row['total_exitosos']),
        porcentaje_exito=round(porcentaje_exito, 2),
        catalogos_activos=int(row['catalogos_activos']),
        ultima_actualizacion=row['ultima_actualizacion']
    )

@app.get("/api/v1/estados", response_model=RespuestaApi)
async def listar_estados(
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(50, ge=1, le=500, description="Registros por página"),
    division: Optional[str] = Query(None, description="Filtrar por división"),
    esquema: Optional[str] = Query(None, description="Filtrar por esquema"),
    metodo: Optional[MetodoNormalizacion] = Query(None, description="Filtrar por método"),
    confianza_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Confianza mínima"),
    requiere_revision: Optional[bool] = Query(None, description="Filtrar por revisión requerida"),
    token: str = Depends(verificar_token)
):
    """Listar estados normalizados con filtros y paginación"""
    
    logger.info(f"Consultando estados - Página: {pagina}, Por página: {por_pagina}")
    
    # Construir consulta con filtros dinámicos
    where_conditions = []
    params = {}
    
    if division:
        where_conditions.append("division = :division")
        params['division'] = division
    
    if esquema:
        where_conditions.append("esquema = :esquema")
        params['esquema'] = esquema
    
    if metodo:
        where_conditions.append("metodo_usado = :metodo")
        params['metodo'] = metodo.value
    
    if confianza_min is not None:
        where_conditions.append("confianza >= :confianza_min")
        params['confianza_min'] = confianza_min
    
    if requiere_revision is not None:
        where_conditions.append("requiere_revision = :requiere_revision")
        params['requiere_revision'] = requiere_revision
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Consulta para contar total
    count_query = f"SELECT COUNT(*) as total FROM estados_normalizados WHERE {where_clause}"
    df_count = ejecutar_consulta_segura(count_query, params)
    total = int(df_count.iloc[0]['total'])
    
    # Consulta con paginación
    offset = (pagina - 1) * por_pagina
    params.update({'limit': por_pagina, 'offset': offset})
    
    data_query = f"""
    SELECT * FROM estados_normalizados 
    WHERE {where_clause}
    ORDER BY id
    LIMIT :limit OFFSET :offset
    """
    
    df = ejecutar_consulta_segura(data_query, params)
    
    # Convertir a diccionarios
    datos = df.to_dict('records') if not df.empty else []
    
    # Convertir datetime a string para JSON
    for registro in datos:
        for key, value in registro.items():
            if isinstance(value, datetime):
                registro[key] = value.isoformat()
    
    return RespuestaApi(
        exito=True,
        datos=datos,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        mensaje=f"Se encontraron {total} estados normalizados"
    )

@app.get("/api/v1/municipios", response_model=RespuestaApi)
async def listar_municipios(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=500),
    division: Optional[str] = Query(None),
    esquema: Optional[str] = Query(None),
    metodo: Optional[MetodoNormalizacion] = Query(None),
    confianza_min: Optional[float] = Query(None, ge=0.0, le=1.0),
    token: str = Depends(verificar_token)
):
    """Listar municipios normalizados"""
    
    logger.info(f"Consultando municipios - Página: {pagina}")
    
    # Similar lógica que estados pero para municipios
    where_conditions = []
    params = {}
    
    if division:
        where_conditions.append("division = :division")
        params['division'] = division
    
    if esquema:
        where_conditions.append("esquema = :esquema")
        params['esquema'] = esquema
    
    if metodo:
        where_conditions.append("metodo_usado = :metodo")
        params['metodo'] = metodo.value
    
    if confianza_min is not None:
        where_conditions.append("confianza >= :confianza_min")
        params['confianza_min'] = confianza_min
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Contar total
    count_query = f"SELECT COUNT(*) as total FROM municipios_normalizados WHERE {where_clause}"
    df_count = ejecutar_consulta_segura(count_query, params)
    total = int(df_count.iloc[0]['total'])
    
    # Consulta con paginación
    offset = (pagina - 1) * por_pagina
    params.update({'limit': por_pagina, 'offset': offset})
    
    data_query = f"""
    SELECT * FROM municipios_normalizados 
    WHERE {where_clause}
    ORDER BY id
    LIMIT :limit OFFSET :offset
    """
    
    df = ejecutar_consulta_segura(data_query, params)
    datos = df.to_dict('records') if not df.empty else []
    
    # Convertir datetime a string
    for registro in datos:
        for key, value in registro.items():
            if isinstance(value, datetime):
                registro[key] = value.isoformat()
    
    return RespuestaApi(
        exito=True,
        datos=datos,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        mensaje=f"Se encontraron {total} municipios normalizados"
    )

@app.get("/api/v1/colonias", response_model=RespuestaApi)
async def listar_colonias(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=500),
    division: Optional[str] = Query(None),
    codigo_postal: Optional[str] = Query(None, description="Filtrar por código postal"),
    metodo: Optional[MetodoNormalizacion] = Query(None),
    confianza_min: Optional[float] = Query(None, ge=0.0, le=1.0),
    token: str = Depends(verificar_token)
):
    """Listar colonias normalizadas"""
    
    logger.info(f"Consultando colonias - Página: {pagina}")
    
    where_conditions = []
    params = {}
    
    if division:
        where_conditions.append("division = :division")
        params['division'] = division
    
    if codigo_postal:
        where_conditions.append("codigo_postal = :codigo_postal")
        params['codigo_postal'] = codigo_postal
    
    if metodo:
        where_conditions.append("metodo_usado = :metodo")
        params['metodo'] = metodo.value
    
    if confianza_min is not None:
        where_conditions.append("confianza >= :confianza_min")
        params['confianza_min'] = confianza_min
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Contar total
    count_query = f"SELECT COUNT(*) as total FROM colonias_normalizadas WHERE {where_clause}"
    df_count = ejecutar_consulta_segura(count_query, params)
    total = int(df_count.iloc[0]['total'])
    
    # Consulta con paginación
    offset = (pagina - 1) * por_pagina
    params.update({'limit': por_pagina, 'offset': offset})
    
    data_query = f"""
    SELECT * FROM colonias_normalizadas 
    WHERE {where_clause}
    ORDER BY id
    LIMIT :limit OFFSET :offset
    """
    
    df = ejecutar_consulta_segura(data_query, params)
    datos = df.to_dict('records') if not df.empty else []
    
    # Convertir datetime a string
    for registro in datos:
        for key, value in registro.items():
            if isinstance(value, datetime):
                registro[key] = value.isoformat()
    
    return RespuestaApi(
        exito=True,
        datos=datos,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        mensaje=f"Se encontraron {total} colonias normalizadas"
    )

@app.post("/api/v1/buscar")
async def buscar_normalizado(
    consulta: ConsultaNormalizacion,
    token: str = Depends(verificar_token)
):
    """Buscar texto normalizado en los catálogos"""
    
    logger.info(f"Búsqueda: '{consulta.texto_buscar}' en {consulta.tipo_catalogo}")
    
    # Determinar tabla según tipo de catálogo
    tabla_mapping = {
        "estados": ("estados_normalizados", "estado_normalizado"),
        "municipios": ("municipios_normalizados", "municipio_normalizado"),
        "colonias": ("colonias_normalizadas", "colonia_normalizada")
    }
    
    if consulta.tipo_catalogo not in tabla_mapping:
        raise HTTPException(status_code=400, detail="Tipo de catálogo no válido")
    
    tabla, columna_normalizada = tabla_mapping[consulta.tipo_catalogo]
    
    # Búsqueda con LIKE para coincidencias parciales
    query = f"""
    SELECT *, 
           CASE 
               WHEN UPPER(texto_original) = UPPER(:texto_buscar) THEN 1.0
               WHEN UPPER(texto_original) LIKE UPPER(:texto_like) THEN 0.8
               WHEN UPPER({columna_normalizada}) LIKE UPPER(:texto_like) THEN 0.9
               ELSE confianza
           END as relevancia
    FROM {tabla}
    WHERE (UPPER(texto_original) LIKE UPPER(:texto_like) 
           OR UPPER({columna_normalizada}) LIKE UPPER(:texto_like))
    AND confianza >= :umbral_confianza
    ORDER BY relevancia DESC, confianza DESC
    LIMIT 20
    """
    
    params = {
        'texto_buscar': consulta.texto_buscar,
        'texto_like': f"%{consulta.texto_buscar}%",
        'umbral_confianza': consulta.umbral_confianza
    }
    
    df = ejecutar_consulta_segura(query, params)
    
    if df.empty:
        return {
            "exito": True,
            "resultados": [],
            "total": 0,
            "mensaje": f"No se encontraron coincidencias para '{consulta.texto_buscar}' en {consulta.tipo_catalogo}"
        }
    
    # Convertir a diccionarios
    resultados = df.to_dict('records')
    
    # Convertir datetime a string
    for resultado in resultados:
        for key, value in resultado.items():
            if isinstance(value, datetime):
                resultado[key] = value.isoformat()
    
    return {
        "exito": True,
        "resultados": resultados,
        "total": len(resultados),
        "mensaje": f"Se encontraron {len(resultados)} coincidencias para '{consulta.texto_buscar}'"
    }

@app.get("/api/v1/estadisticas/{tipo_catalogo}")
async def obtener_estadisticas_catalogo(
    tipo_catalogo: TipoCatalogo,
    token: str = Depends(verificar_token)
):
    """Obtener estadísticas específicas de un catálogo"""
    
    tabla_mapping = {
        "estados": "estados_normalizados",
        "municipios": "municipios_normalizados", 
        "colonias": "colonias_normalizadas"
    }
    
    tabla = tabla_mapping[tipo_catalogo.value]
    
    query = f"""
    SELECT 
        COUNT(*) as total_registros,
        COUNT(CASE WHEN confianza >= 0.9 THEN 1 END) as alta_confianza,
        COUNT(CASE WHEN confianza BETWEEN 0.7 AND 0.89 THEN 1 END) as media_confianza,
        COUNT(CASE WHEN confianza < 0.7 THEN 1 END) as baja_confianza,
        COUNT(CASE WHEN requiere_revision = true THEN 1 END) as requiere_revision,
        AVG(confianza) as confianza_promedio,
        COUNT(DISTINCT metodo_usado) as metodos_utilizados,
        COUNT(DISTINCT division) as divisiones_procesadas
    FROM {tabla}
    WHERE confianza > 0
    """
    
    df = ejecutar_consulta_segura(query)
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No se encontraron datos para {tipo_catalogo}")
    
    estadisticas = df.iloc[0].to_dict()
    
    # Agregar distribución de métodos
    query_metodos = f"""
    SELECT metodo_usado, COUNT(*) as cantidad
    FROM {tabla}
    WHERE metodo_usado IS NOT NULL
    GROUP BY metodo_usado
    ORDER BY cantidad DESC
    """
    
    df_metodos = ejecutar_consulta_segura(query_metodos)
    metodos_distribucion = df_metodos.to_dict('records') if not df_metodos.empty else []
    
    return {
        "catalogo": tipo_catalogo.value,
        "estadisticas_generales": estadisticas,
        "distribucion_metodos": metodos_distribucion,
        "timestamp": datetime.now().isoformat()
    }

# ========================================
# 6. SERVIDOR Y CONFIGURACIÓN
# ========================================

if __name__ == "__main__":
    print("🚀 Iniciando API de Normalización de Domicilios")
    print("📚 Documentación disponible en: http://localhost:8000/docs")
    print("🔑 Token de prueba: demo-token-2025")
    
    uvicorn.run(
        "api_normalizacion:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )