# ========================================
# ARCHIVO: crear_datos_expandidos.py
# SISTEMA EXPANDIDO - MUNICIPIOS, CIUDADES, COLONIAS
# ========================================

"""
💡 ¿QUÉ HACE ESTE ARCHIVO?
Crea datos de prueba más completos para simular el mundo real:
- Estados (ya tenemos)
- Municipios (nuevo)
- Ciudades (nuevo) 
- Colonias (nuevo - el gran desafío)

Esto nos permitirá probar el sistema con casos más complejos
antes de usar los datos reales de 9 millones de registros.
"""

import pandas as pd
import os
import random
from datetime import datetime, timedelta

print("🚀 CREANDO SISTEMA EXPANDIDO DE NORMALIZACIÓN...")

# ========================================
# 1. CREAR ESTRUCTURA EXPANDIDA
# ========================================

def crear_estructura_expandida():
    """Crear carpetas para el sistema expandido"""
    
    carpetas = [
        "data/raw/DES/municipios",
        "data/raw/DES/ciudades", 
        "data/raw/DES/colonias",
        "data/reference/sepomex/municipios",
        "data/reference/sepomex/ciudades",
        "data/reference/sepomex/colonias",
        "data/processed/DES/municipios",
        "data/processed/DES/ciudades",
        "data/processed/DES/colonias",
        "reportes/ejecutivos",
        "reportes/detallados"
    ]
    
    for carpeta in carpetas:
        os.makedirs(carpeta, exist_ok=True)
        print(f"   ✅ {carpeta}")

# ========================================
# 2. DATOS DE MUNICIPIOS
# ========================================

def crear_municipios_referencia():
    """Crear catálogo de municipios con datos reales de México"""
    
    print("\n🏛️ Creando catálogo de municipios...")
    
    # Municipios reales de México (muestra representativa)
    municipios_mexico = [
        # Aguascalientes
        {'estado': 'AGUASCALIENTES', 'clave_mun': '001', 'nombre': 'AGUASCALIENTES', 'lat': 21.8853, 'lng': -102.2916, 'poblacion': 948990},
        {'estado': 'AGUASCALIENTES', 'clave_mun': '002', 'nombre': 'ASIENTOS', 'lat': 22.2386, 'lng': -102.0889, 'poblacion': 50271},
        {'estado': 'AGUASCALIENTES', 'clave_mun': '003', 'nombre': 'CALVILLO', 'lat': 21.8469, 'lng': -102.7186, 'poblacion': 56048},
        
        # Baja California
        {'estado': 'BAJA CALIFORNIA', 'clave_mun': '001', 'nombre': 'ENSENADA', 'lat': 31.8661, 'lng': -116.5956, 'poblacion': 542896},
        {'estado': 'BAJA CALIFORNIA', 'clave_mun': '002', 'nombre': 'MEXICALI', 'lat': 32.6519, 'lng': -115.4683, 'poblacion': 1049792},
        {'estado': 'BAJA CALIFORNIA', 'clave_mun': '003', 'nombre': 'TECATE', 'lat': 32.5341, 'lng': -116.6275, 'poblacion': 108440},
        {'estado': 'BAJA CALIFORNIA', 'clave_mun': '004', 'nombre': 'TIJUANA', 'lat': 32.5149, 'lng': -117.0382, 'poblacion': 1810645},
        {'estado': 'BAJA CALIFORNIA', 'clave_mun': '005', 'nombre': 'PLAYAS DE ROSARITO', 'lat': 32.3668, 'lng': -117.0648, 'poblacion': 126890},
        
        # Ciudad de México (Alcaldías)
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '001', 'nombre': 'AZCAPOTZALCO', 'lat': 19.4909, 'lng': -99.1861, 'poblacion': 432205},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '002', 'nombre': 'COYOACÁN', 'lat': 19.3467, 'lng': -99.1618, 'poblacion': 614447},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '003', 'nombre': 'CUAJIMALPA DE MORELOS', 'lat': 19.3650, 'lng': -99.2933, 'poblacion': 217686},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '004', 'nombre': 'GUSTAVO A. MADERO', 'lat': 19.4896, 'lng': -99.1147, 'poblacion': 1164477},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '005', 'nombre': 'IZTACALCO', 'lat': 19.4126, 'lng': -99.1124, 'poblacion': 404695},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '006', 'nombre': 'IZTAPALAPA', 'lat': 19.3573, 'lng': -99.0535, 'poblacion': 1835486},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '007', 'nombre': 'LA MAGDALENA CONTRERAS', 'lat': 19.3018, 'lng': -99.2395, 'poblacion': 247622},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '008', 'nombre': 'MILPA ALTA', 'lat': 19.1924, 'lng': -99.0238, 'poblacion': 152685},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '009', 'nombre': 'ÁLVARO OBREGÓN', 'lat': 19.3723, 'lng': -99.2394, 'poblacion': 759137},
        {'estado': 'CIUDAD DE MÉXICO', 'clave_mun': '010', 'nombre': 'TLÁHUAC', 'lat': 19.2864, 'lng': -99.0134, 'poblacion': 392313},
        
        # Estado de México (principales)
        {'estado': 'MÉXICO', 'clave_mun': '001', 'nombre': 'ACAMBAY DE RUÍZ CASTAÑEDA', 'lat': 19.9394, 'lng': -99.8472, 'poblacion': 68571},
        {'estado': 'MÉXICO', 'clave_mun': '013', 'nombre': 'ATIZAPÁN DE ZARAGOZA', 'lat': 19.5806, 'lng': -99.2547, 'poblacion': 523296},
        {'estado': 'MÉXICO', 'clave_mun': '020', 'nombre': 'COACALCO DE BERRIOZÁBAL', 'lat': 19.6319, 'lng': -99.1072, 'poblacion': 293444},
        {'estado': 'MÉXICO', 'clave_mun': '025', 'nombre': 'CUAUTITLÁN', 'lat': 19.6694, 'lng': -99.1764, 'poblacion': 149550},
        {'estado': 'MÉXICO', 'clave_mun': '028', 'nombre': 'CUAUTITLÁN IZCALLI', 'lat': 19.6464, 'lng': -99.2403, 'poblacion': 555803},
        {'estado': 'MÉXICO', 'clave_mun': '033', 'nombre': 'ECATEPEC DE MORELOS', 'lat': 19.6197, 'lng': -99.0642, 'poblacion': 1645352},
        {'estado': 'MÉXICO', 'clave_mun': '037', 'nombre': 'HUIXQUILUCAN', 'lat': 19.3647, 'lng': -99.3497, 'poblacion': 267858},
        {'estado': 'MÉXICO', 'clave_mun': '053', 'nombre': 'NAUCALPAN DE JUÁREZ', 'lat': 19.4781, 'lng': -99.2381, 'poblacion': 833779},
        {'estado': 'MÉXICO', 'clave_mun': '058', 'nombre': 'NEZAHUALCÓYOTL', 'lat': 19.4003, 'lng': -99.0142, 'poblacion': 1077208},
        {'estado': 'MÉXICO', 'clave_mun': '081', 'nombre': 'TLALNEPANTLA DE BAZ', 'lat': 19.5408, 'lng': -99.1950, 'poblacion': 700734},
        {'estado': 'MÉXICO', 'clave_mun': '104', 'nombre': 'TOLUCA', 'lat': 19.2889, 'lng': -99.6561, 'poblacion': 910608},
        
        # Jalisco (principales) 
        {'estado': 'JALISCO', 'clave_mun': '020', 'nombre': 'GUADALAJARA', 'lat': 20.6597, 'lng': -103.3496, 'poblacion': 1385629},
        {'estado': 'JALISCO', 'clave_mun': '097', 'nombre': 'TLAQUEPAQUE', 'lat': 20.6401, 'lng': -103.2893, 'poblacion': 687127},
        {'estado': 'JALISCO', 'clave_mun': '101', 'nombre': 'TONALÁ', 'lat': 20.6231, 'lng': -103.2333, 'poblacion': 568960},
        {'estado': 'JALISCO', 'clave_mun': '124', 'nombre': 'ZAPOPAN', 'lat': 20.7227, 'lng': -103.3844, 'poblacion': 1476491},
        
        # Nuevo León (principales)
        {'estado': 'NUEVO LEÓN', 'clave_mun': '019', 'nombre': 'GUADALUPE', 'lat': 25.6767, 'lng': -100.2578, 'poblacion': 678006},
        {'estado': 'NUEVO LEÓN', 'clave_mun': '039', 'nombre': 'MONTERREY', 'lat': 25.6866, 'lng': -100.3161, 'poblacion': 1135512},
        {'estado': 'NUEVO LEÓN', 'clave_mun': '046', 'nombre': 'SAN NICOLÁS DE LOS GARZA', 'lat': 25.7415, 'lng': -100.2864, 'poblacion': 443273},
        {'estado': 'NUEVO LEÓN', 'clave_mun': '048', 'nombre': 'SAN PEDRO GARZA GARCÍA', 'lat': 25.6522, 'lng': -100.4061, 'poblacion': 122659}
    ]
    
    df_municipios = pd.DataFrame(municipios_mexico)
    
    # Guardar archivo
    archivo = "data/reference/sepomex/municipios/municipios_mexico.csv"
    df_municipios.to_csv(archivo, index=False, encoding='utf-8')
    
    print(f"   ✅ Creados {len(df_municipios)} municipios de referencia")
    print(f"   📁 Guardado en: {archivo}")
    
    return df_municipios

def crear_municipios_as400_sucios():
    """Crear datos 'sucios' de municipios como vendrían de AS400"""
    
    print("\n🏗️ Creando datos sucios de municipios AS400...")
    
    # Datos sucios que simulan problemas reales
    municipios_sucios_dds = [
        # Datos con errores típicos
        ['DES', 'DDS', '001', 'AGUASCALIENTES', '2025-05-28'],
        ['DES', 'DDS', '002', 'ASIENTOS', '2025-05-28'],
        ['DES', 'DDS', '003', 'CALVILLO', '2025-05-28'],
        ['DES', 'DDS', '001', 'ENSENADA', '2025-05-28'],
        ['DES', 'DDS', '002', 'MEXICALI', '2025-05-28'],
        ['DES', 'DDS', '003', 'TECATE', '2025-05-28'],
        ['DES', 'DDS', '004', 'TIJUANA', '2025-05-28'],
        ['DES', 'DDS', '001', 'AZCAPOTZALCO', '2025-05-28'],
        ['DES', 'DDS', '002', 'COYOACAN', '2025-05-28'],  # Sin acento
        ['DES', 'DDS', '003', 'CUAJIMALPA', '2025-05-28'],  # Nombre incompleto
        ['DES', 'DDS', '004', 'GAM', '2025-05-28'],  # Abreviación de Gustavo A. Madero
        ['DES', 'DDS', '006', 'IZTAPALAPA', '2025-05-28'],
        ['DES', 'DDS', '033', 'ECATEPEC', '2025-05-28'],  # Nombre incompleto
        ['DES', 'DDS', '058', 'NEZA', '2025-05-28'],  # Abreviación de Nezahualcóyotl
        ['DES', 'DDS', '081', 'TLALNEPANTLA', '2025-05-28'],  # Sin "DE BAZ"
        ['DES', 'DDS', '104', 'TOLUCA', '2025-05-28'],
        ['DES', 'DDS', '020', 'GUADALAJARA', '2025-05-28'],
        ['DES', 'DDS', '039', 'MONTERREY', '2025-05-28'],
    ]
    
    municipios_sucios_db2 = [
        # Más variaciones y abreviaciones 
        ['DES', 'DB2', 'AGS001', 'AGUASCALIENTES', '2025-05-28'],
        ['DES', 'DB2', 'BC001', 'ENSENADA', '2025-05-28'],
        ['DES', 'DB2', 'BC002', 'MEXICALI', '2025-05-28'],
        ['DES', 'DB2', 'BC004', 'TIJUANA', '2025-05-28'],
        ['DES', 'DB2', 'DF001', 'AZCAPOTZALCO', '2025-05-28'],  # Todavía usa DF
        ['DES', 'DB2', 'DF002', 'COYOACAN', '2025-05-28'],
        ['DES', 'DB2', 'DF004', 'GUSTAVO A MADERO', '2025-05-28'],  # Sin punto
        ['DES', 'DB2', 'DF006', 'IZTAPALAPA', '2025-05-28'],
        ['DES', 'DB2', 'MEX033', 'ECATEPEC DE MORELOS', '2025-05-28'],  # Completo
        ['DES', 'DB2', 'MEX058', 'NEZAHUALCOYOTL', '2025-05-28'],  # Sin acento
        ['DES', 'DB2', 'MEX081', 'TLALNEPANTLA DE BAZ', '2025-05-28'],  # Completo
        ['DES', 'DB2', 'MEX104', 'TOLUCA', '2025-05-28'],
        ['DES', 'DB2', 'JAL020', 'GUADALAJARA', '2025-05-28'],
        ['DES', 'DB2', 'NL039', 'MONTERREY', '2025-05-28'],
        # Algunos datos basura
        ['DES', 'DB2', 'XXX999', 'MUNICIPIO_INEXISTENTE', '2025-05-28'],
        ['DES', 'DB2', '', 'SIN_CLAVE_MUN', '2025-05-28'],
    ]
    
    # Crear DataFrames
    df_dds = pd.DataFrame(municipios_sucios_dds, columns=[
        'division', 'esquema', 'clave_original', 'nombre_original', 'fecha_extraccion'
    ])
    
    df_db2 = pd.DataFrame(municipios_sucios_db2, columns=[
        'division', 'esquema', 'clave_original', 'nombre_original', 'fecha_extraccion'
    ])
    
    # Guardar archivos
    archivo_dds = "data/raw/DES/municipios/municipios_dds.csv"
    archivo_db2 = "data/raw/DES/municipios/municipios_db2.csv"
    
    df_dds.to_csv(archivo_dds, index=False, encoding='utf-8')
    df_db2.to_csv(archivo_db2, index=False, encoding='utf-8')
    
    print(f"   ✅ DDS: {len(df_dds)} municipios sucios")
    print(f"   ✅ DB2: {len(df_db2)} municipios sucios")
    
    return df_dds, df_db2

# ========================================
# 3. DATOS DE COLONIAS (EL GRAN DESAFÍO)
# ========================================

def crear_colonias_referencia():
    """Crear un subconjunto representativo de colonias mexicanas"""
    
    print("\n🏘️ Creando catálogo de colonias (muestra)...")
    
    # Colonias reales de diferentes ciudades (muestra representativa)
    colonias_mexico = [
        # Ciudad de México
        {'municipio': 'IZTAPALAPA', 'codigo_postal': '09010', 'colonia': 'SANTA CRUZ MEYEHUALCO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'IZTAPALAPA', 'codigo_postal': '09020', 'colonia': 'AÑO DE JUÁREZ', 'tipo_asent': 'COLONIA'},
        {'municipio': 'IZTAPALAPA', 'codigo_postal': '09030', 'colonia': 'GRANJAS SAN ANTONIO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'COYOACÁN', 'codigo_postal': '04100', 'colonia': 'DEL CARMEN', 'tipo_asent': 'COLONIA'},
        {'municipio': 'COYOACÁN', 'codigo_postal': '04120', 'colonia': 'COPILCO UNIVERSIDAD', 'tipo_asent': 'COLONIA'},
        {'municipio': 'ÁLVARO OBREGÓN', 'codigo_postal': '01000', 'colonia': 'SAN ÁNGEL', 'tipo_asent': 'COLONIA'},
        {'municipio': 'ÁLVARO OBREGÓN', 'codigo_postal': '01010', 'colonia': 'SAN ÁNGEL INN', 'tipo_asent': 'COLONIA'},
        {'municipio': 'GUSTAVO A. MADERO', 'codigo_postal': '07000', 'colonia': 'LINDAVISTA NORTE', 'tipo_asent': 'COLONIA'},
        {'municipio': 'GUSTAVO A. MADERO', 'codigo_postal': '07010', 'colonia': 'LINDAVISTA SUR', 'tipo_asent': 'COLONIA'},
        
        # Guadalajara
        {'municipio': 'GUADALAJARA', 'codigo_postal': '44100', 'colonia': 'CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'GUADALAJARA', 'codigo_postal': '44110', 'colonia': 'ZONA CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'GUADALAJARA', 'codigo_postal': '44120', 'colonia': 'AMERICANA', 'tipo_asent': 'COLONIA'},
        {'municipio': 'ZAPOPAN', 'codigo_postal': '45010', 'colonia': 'CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'ZAPOPAN', 'codigo_postal': '45020', 'colonia': 'BELISARIO DOMÍNGUEZ', 'tipo_asent': 'COLONIA'},
        
        # Monterrey
        {'municipio': 'MONTERREY', 'codigo_postal': '64000', 'colonia': 'CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'MONTERREY', 'codigo_postal': '64010', 'colonia': 'ANCIRA', 'tipo_asent': 'COLONIA'},
        {'municipio': 'MONTERREY', 'codigo_postal': '64020', 'colonia': 'BELLA VISTA', 'tipo_asent': 'COLONIA'},
        {'municipio': 'SAN NICOLÁS DE LOS GARZA', 'codigo_postal': '66400', 'colonia': 'CENTRO', 'tipo_asent': 'COLONIA'},
        
        # Tijuana
        {'municipio': 'TIJUANA', 'codigo_postal': '22000', 'colonia': 'ZONA CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'TIJUANA', 'codigo_postal': '22010', 'colonia': 'ZONA NORTE', 'tipo_asent': 'COLONIA'},
        {'municipio': 'TIJUANA', 'codigo_postal': '22020', 'colonia': 'ZONA RÍO', 'tipo_asent': 'COLONIA'},
        
        # Estado de México
        {'municipio': 'NEZAHUALCÓYOTL', 'codigo_postal': '57000', 'colonia': 'CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'NEZAHUALCÓYOTL', 'codigo_postal': '57100', 'colonia': 'BENITO JUÁREZ', 'tipo_asent': 'COLONIA'},
        {'municipio': 'ECATEPEC DE MORELOS', 'codigo_postal': '55000', 'colonia': 'ECATEPEC CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'NAUCALPAN DE JUÁREZ', 'codigo_postal': '53000', 'colonia': 'NAUCALPAN CENTRO', 'tipo_asent': 'COLONIA'},
        {'municipio': 'TLALNEPANTLA DE BAZ', 'codigo_postal': '54000', 'colonia': 'TLALNEPANTLA CENTRO', 'tipo_asent': 'COLONIA'},
        
        # Algunos fraccionamientos y unidades habitacionales
        {'municipio': 'GUADALAJARA', 'codigo_postal': '44500', 'colonia': 'JARDINES DE GUADALUPE', 'tipo_asent': 'FRACCIONAMIENTO'},
        {'municipio': 'MONTERREY', 'codigo_postal': '64700', 'colonia': 'RESIDENCIAL SAN AGUSTÍN', 'tipo_asent': 'FRACCIONAMIENTO'},
        {'municipio': 'TIJUANA', 'codigo_postal': '22500', 'colonia': 'HIPÓDROMO', 'tipo_asent': 'FRACCIONAMIENTO'},
        {'municipio': 'NEZAHUALCÓYOTL', 'codigo_postal': '57200', 'colonia': 'IMPULSORA POPULAR AVÍCOLA', 'tipo_asent': 'UNIDAD HABITACIONAL'},
    ]
    
    df_colonias = pd.DataFrame(colonias_mexico)
    
    # Agregar coordenadas simuladas (en el mundo real vendrían de SEPOMEX)
    df_colonias['lat'] = [round(random.uniform(19.0, 32.0), 6) for _ in range(len(df_colonias))]
    df_colonias['lng'] = [round(random.uniform(-117.0, -86.0), 6) for _ in range(len(df_colonias))]
    
    archivo = "data/reference/sepomex/colonias/colonias_mexico.csv"
    df_colonias.to_csv(archivo, index=False, encoding='utf-8')
    
    print(f"   ✅ Creadas {len(df_colonias)} colonias de referencia")
    print(f"   📁 Guardado en: {archivo}")
    
    return df_colonias

def crear_colonias_as400_sucias():
    """Crear datos sucios de colonias como vendrían de AS400"""
    
    print("\n🏗️ Creando datos sucios de colonias AS400...")
    
    # Generar datos sucios más variados para colonias
    colonias_sucias = []
    
    # Casos típicos de datos sucios en colonias
    casos_sucios = [
        # Casos normales
        ('09010', 'SANTA CRUZ MEYEHUALCO'),
        ('09020', 'AÑO DE JUAREZ'),  # Sin acento
        ('09030', 'GRANJAS SAN ANTONIO'), 
        ('04100', 'DEL CARMEN'),
        ('04120', 'COPILCO UNIVERSIDAD'),
        ('01000', 'SAN ANGEL'),  # Sin acento
        ('07000', 'LINDAVISTA NORTE'),
        
        # Casos con errores típicos
        ('44100', 'CENTRO GDL'),  # Abreviación
        ('44120', 'AMERICANA'),
        ('45010', 'CENTRO ZAPOPAN'),  # Nombre extendido
        ('64000', 'CENTRO MTY'),  # Abreviación
        ('64010', 'ANCIRA'),
        ('22000', 'ZONA CENTRO TIJUANA'),  # Nombre extendido
        ('57000', 'CENTRO NEZA'),  # Abreviación
        ('55000', 'ECATEPEC CENTRO'),
        
        # Casos problemáticos
        ('44500', 'JARDINES GUADALUPE'),  # Sin "DE"
        ('64700', 'RESIDENCIAL SAN AGUSTIN'),  # Sin acento
        ('22500', 'HIPODROMO'),  # Sin acento
        ('57200', 'IMPULSORA POPULAR'),  # Nombre incompleto
        
        # Algunos casos de basura
        ('00000', 'COLONIA_INEXISTENTE'),
        ('99999', 'BASURA123'),
        ('', 'SIN_CODIGO_POSTAL'),
    ]
    
    # Crear datos para DDS
    for i, (cp, colonia) in enumerate(casos_sucios):
        colonias_sucias.append([
            'DES', 'DDS', f'COL{i:03d}', cp, colonia, '2025-05-28'
        ])
    
    df_colonias_dds = pd.DataFrame(colonias_sucias, columns=[
        'division', 'esquema', 'clave_original', 'codigo_postal', 'nombre_original', 'fecha_extraccion'
    ])
    
    # Crear variaciones para DB2 con más errores
    colonias_db2 = []
    for i, (cp, colonia) in enumerate(casos_sucios[:20]):  # Menos registros para DB2
        # Agregar más variaciones
        colonia_variada = colonia.replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
        colonias_db2.append([
            'DES', 'DB2', f'DB2COL{i:03d}', cp, colonia_variada, '2025-05-28'
        ])
    
    df_colonias_db2 = pd.DataFrame(colonias_db2, columns=[
        'division', 'esquema', 'clave_original', 'codigo_postal', 'nombre_original', 'fecha_extraccion'
    ])
    
    # Guardar archivos
    archivo_dds = "data/raw/DES/colonias/colonias_dds.csv"
    archivo_db2 = "data/raw/DES/colonias/colonias_db2.csv"
    
    df_colonias_dds.to_csv(archivo_dds, index=False, encoding='utf-8')
    df_colonias_db2.to_csv(archivo_db2, index=False, encoding='utf-8')
    
    print(f"   ✅ DDS: {len(df_colonias_dds)} colonias sucias")
    print(f"   ✅ DB2: {len(df_colonias_db2)} colonias sucias")
    
    return df_colonias_dds, df_colonias_db2

# ========================================
# 4. SIMULADOR DE DATOS MASIVOS
# ========================================

def simular_datos_masivos():
    """
    💡 Simula el escenario real de 9 millones de registros
    Crea una muestra representativa para probar escalabilidad
    """
    
    print("\n📊 Simulando datos masivos (muestra representativa)...")
    
    # Patrones de nombres reales que se repiten en México
    patrones_colonias = [
        'CENTRO', 'LOMAS DE', 'JARDINES DE', 'FRACCIONAMIENTO', 'RESIDENCIAL',
        'UNIDAD HABITACIONAL', 'CONJUNTO HABITACIONAL', 'VILLAS DE', 'RINCON DE',
        'SANTA', 'SAN', 'NUEVA', 'VIEJA', 'AMPLIACION', 'BARRIO', 'PUEBLO',
        'INDUSTRIAL', 'COMERCIAL', 'ZONA', 'SECTOR', 'MANZANA', 'LOTE'
    ]
    
    # Crear datos masivos simulados
    registros_masivos = []
    
    for i in range(500):  # 500 registros para prueba (simula 9M)
        # Generar nombre de colonia aleatorio pero realista
        patron = random.choice(patrones_colonias)
        numero = random.randint(1, 999)
        nombre_colonia = f"{patron} {numero}"
        
        # Agregar errores aleatorios como en datos reales
        if random.random() < 0.3:  # 30% de datos con errores
            # Quitar acentos
            nombre_colonia = nombre_colonia.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
        
        if random.random() < 0.2:  # 20% con abreviaciones
            nombre_colonia = nombre_colonia.replace('FRACCIONAMIENTO', 'FRACC').replace('RESIDENCIAL', 'RESID')
        
        if random.random() < 0.1:  # 10% con espacios extra o caracteres raros
            nombre_colonia = f"  {nombre_colonia}  " if random.random() < 0.5 else f"{nombre_colonia}_123"
        
        # Generar código postal aleatorio
        codigo_postal = f"{random.randint(10000, 99999):05d}"
        
        registros_masivos.append([
            'DES', 'MASIVO', f'MASS{i:06d}', codigo_postal, nombre_colonia, 
            (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d')
        ])
    
    df_masivo = pd.DataFrame(registros_masivos, columns=[
        'division', 'esquema', 'clave_original', 'codigo_postal', 'nombre_original', 'fecha_extraccion'
    ])
    
    archivo_masivo = "data/raw/DES/colonias/colonias_masivo_muestra.csv"
    df_masivo.to_csv(archivo_masivo, index=False, encoding='utf-8')
    
    print(f"   ✅ Simulados {len(df_masivo)} registros masivos")
    print(f"   📊 Esto representa una muestra de los 9M reales")
    print(f"   📁 Guardado en: {archivo_masivo}")
    
    return df_masivo

# ========================================
# 5. GENERADOR DE REPORTES EJECUTIVOS
# ========================================

def crear_plantilla_reporte_ejecutivo():
    """Crear plantilla HTML para reportes ejecutivos impresionantes"""
    
    print("\n📋 Creando plantilla de reporte ejecutivo...")
    
    plantilla_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Ejecutivo - Normalización de Domicilios</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            color: #666;
            font-size: 1.2em;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .metric-label {
            color: #666;
            font-size: 1.1em;
            font-weight: 600;
        }
        
        .section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .section h2 {
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        
        .progress-bar {
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .table th, .table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .table th {
            background: #667eea;
            color: white;
            font-weight: 600;
        }
        
        .table tr:hover {
            background: #f5f5f5;
        }
        
        .status-success {
            color: #4caf50;
            font-weight: bold;
        }
        
        .status-warning {
            color: #ff9800;
            font-weight: bold;
        }
        
        .status-error {
            color: #f44336;
            font-weight: bold;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9em;
        }
        
        @media print {
            body {
                background: white;
            }
            .metric-card, .section, .header {
                box-shadow: none;
                border: 1px solid #ddd;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Reporte Ejecutivo</h1>
            <p class="subtitle">Sistema de Normalización de Domicilios | División DES</p>
            <p class="subtitle">Generado el: {fecha_reporte}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{total_registros:,}</div>
                <div class="metric-label">Total Registros Procesados</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{porcentaje_exito}%</div>
                <div class="metric-label">Tasa de Éxito</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{confianza_promedio}%</div>
                <div class="metric-label">Confianza Promedio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{ahorro_estimado}</div>
                <div class="metric-label">Ahorro Estimado</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Resumen Ejecutivo</h2>
            <p>El sistema de normalización de domicilios ha procesado exitosamente <strong>{total_registros:,} registros</strong> 
            con una tasa de éxito del <strong>{porcentaje_exito}%</strong>. Los resultados superan las expectativas iniciales 
            y demuestran la efectividad de la implementación de inteligencia artificial para la limpieza de datos.</p>
            
            <h3>🎯 Logros Principales:</h3>
            <ul>
                <li>✅ <strong>Normalización automática</strong> de estados, municipios y colonias</li>
                <li>✅ <strong>Detección inteligente</strong> de equivalencias (ej: "DF" → "Ciudad de México")</li>
                <li>✅ <strong>Identificación de datos basura</strong> para limpieza manual</li>
                <li>✅ <strong>Dashboard en tiempo real</strong> para monitoreo continuo</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>📊 Métricas por Esquema</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Esquema</th>
                        <th>Registros</th>
                        <th>Éxito</th>
                        <th>Confianza</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {tabla_esquemas}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>💰 Impacto Económico</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{horas_ahorradas}</div>
                    <div class="metric-label">Horas Ahorradas/Mes</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{citas_mejoradas}%</div>
                    <div class="metric-label">Mejora en Citas</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{roi_estimado}%</div>
                    <div class="metric-label">ROI Estimado</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🚀 Próximos Pasos</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progreso_proyecto}%"></div>
            </div>
            <p>Progreso del Proyecto: <strong>{progreso_proyecto}%</strong></p>
            
            <h3>🎯 Roadmap:</h3>
            <ul>
                <li>✅ <strong>Fase 1:</strong> Estados (Completado)</li>
                <li>🔄 <strong>Fase 2:</strong> Municipios (En progreso)</li>
                <li>📋 <strong>Fase 3:</strong> Colonias (Planificado)</li>
                <li>📋 <strong>Fase 4:</strong> Escalamiento a producción (Q2 2025)</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>⚠️ Recomendaciones</h2>
            <ul>
                <li><strong>Implementación inmediata:</strong> Aplicar normalización de estados a producción</li>
                <li><strong>Capacitación:</strong> Entrenar al equipo en el uso del dashboard</li>
                <li><strong>Monitoreo:</strong> Revisar semanalmente los casos que requieren validación manual</li>
                <li><strong>Escalamiento:</strong> Preparar infraestructura para procesar 9M de registros</li>
            </ul>
        </div>
    </div>
    
    <div class="footer">
        <p>🏢 Sistema desarrollado por el equipo de Data Science | 📧 Contacto: equipo.datos@empresa.com</p>
        <p>🔒 Confidencial - Solo para uso interno</p>
    </div>
</body>
</html>
    """
    
    # Guardar plantilla
    archivo_plantilla = "reportes/ejecutivos/plantilla_reporte.html"
    with open(archivo_plantilla, 'w', encoding='utf-8') as f:
        f.write(plantilla_html)
    
    print(f"   ✅ Plantilla creada: {archivo_plantilla}")
    
    return archivo_plantilla

# ========================================
# 6. FUNCIÓN PRINCIPAL
# ========================================

def main():
    """Función principal para crear todo el sistema expandido"""
    
    print("🚀 INICIANDO CREACIÓN DEL SISTEMA EXPANDIDO...")
    print("=" * 60)
    
    # Crear estructura
    print("\n📁 PASO 1: Creando estructura de carpetas...")
    crear_estructura_expandida()
    
    # Crear datos de municipios
    print("\n🏛️ PASO 2: Creando datos de municipios...")
    df_municipios_ref = crear_municipios_referencia()
    df_mun_dds, df_mun_db2 = crear_municipios_as400_sucios()
    
    # Crear datos de colonias
    print("\n🏘️ PASO 3: Creando datos de colonias...")
    df_colonias_ref = crear_colonias_referencia()
    df_col_dds, df_col_db2 = crear_colonias_as400_sucias()
    
    # Simular datos masivos
    print("\n📊 PASO 4: Simulando datos masivos...")
    df_masivo = simular_datos_masivos()
    
    # Crear plantilla de reporte
    print("\n📋 PASO 5: Creando plantilla de reporte ejecutivo...")
    plantilla = crear_plantilla_reporte_ejecutivo()
    
    # Resumen final
    print("\n🎉 SISTEMA EXPANDIDO CREADO EXITOSAMENTE!")
    print("=" * 60)
    print(f"📊 Municipios de referencia: {len(df_municipios_ref)}")
    print(f"🏛️ Municipios AS400 DDS: {len(df_mun_dds)}")
    print(f"🏛️ Municipios AS400 DB2: {len(df_mun_db2)}")
    print(f"🏘️ Colonias de referencia: {len(df_colonias_ref)}")
    print(f"🏘️ Colonias AS400 DDS: {len(df_col_dds)}")
    print(f"🏘️ Colonias AS400 DB2: {len(df_col_db2)}")
    print(f"📊 Muestra masiva: {len(df_masivo)} registros")
    
    print("\n🚀 PRÓXIMOS PASOS:")
    print("1. Ejecutar: python crear_datos_expandidos.py")
    print("2. Ejecutar: python algoritmo_expandido.py")
    print("3. Ver dashboard actualizado con nuevos datos")
    print("4. Generar reportes ejecutivos")
    
    return True

# ========================================
# 7. EJECUCIÓN
# ========================================

if __name__ == "__main__":
    main()