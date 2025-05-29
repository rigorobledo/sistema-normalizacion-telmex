# ========================================
# ARCHIVO: crear_datos_prueba.py
# PROPÓSITO: Crear datos de ejemplo para probar nuestro sistema
# NIVEL: SÚPER PRINCIPIANTE
# ========================================

"""
💡 ¿QUÉ HACE ESTE ARCHIVO?
Este archivo crea datos de ejemplo que simulan lo que vendrá de AS400.
Es como crear una maqueta antes de construir la casa real.

¿Por qué necesitamos datos de prueba?
- Para probar nuestro código antes de usar datos reales
- Para asegurarnos que todo funciona
- Para mostrar cómo se verá el resultado final
"""

import pandas as pd
import os
from config import PATHS, FILES

# ========================================
# 1. DATOS DE PRUEBA - ESTADOS AS400
# ========================================

def crear_estados_as400_prueba():
    """
    💡 Crear datos que simulan lo que viene de AS400
    Incluimos varios casos para probar nuestro algoritmo:
    - Datos correctos
    - Datos con errores típicos
    - Datos con abreviaciones
    - "Basura" (datos que no sirven)
    """
    
    print("📝 Creando datos de prueba de AS400...")
    
    # Datos del esquema DDS (Data Description Specifications)
    estados_dds = [
        # Formato: division, esquema, clave_original, nombre_original, fecha_extraccion
        ['DES', 'DDS', '01', 'AGUASCALIENTES', '2025-05-28'],
        ['DES', 'DDS', '02', 'BAJA CALIFORNIA', '2025-05-28'],
        ['DES', 'DDS', '03', 'BAJA CALIFORNIA SUR', '2025-05-28'],
        ['DES', 'DDS', '04', 'CAMPECHE', '2025-05-28'],
        ['DES', 'DDS', '05', 'COAHUILA', '2025-05-28'],  # Sin "DE ZARAGOZA"
        ['DES', 'DDS', '06', 'COLIMA', '2025-05-28'],
        ['DES', 'DDS', '07', 'CHIAPAS', '2025-05-28'],
        ['DES', 'DDS', '08', 'CHIHUAHUA', '2025-05-28'],
        ['DES', 'DDS', '09', 'DISTRITO FEDERAL', '2025-05-28'],  # Nombre viejo
        ['DES', 'DDS', '10', 'DURANGO', '2025-05-28'],
        ['DES', 'DDS', '11', 'GUANAJUATO', '2025-05-28'],
        ['DES', 'DDS', '12', 'GUERRERO', '2025-05-28'],
        ['DES', 'DDS', '13', 'HIDALGO', '2025-05-28'],
        ['DES', 'DDS', '14', 'JALISCO', '2025-05-28'],
        ['DES', 'DDS', '15', 'EDO DE MEXICO', '2025-05-28'],  # Abreviación
        ['DES', 'DDS', '16', 'MICHOACAN', '2025-05-28'],  # Sin acentos
        ['DES', 'DDS', '17', 'MORELOS', '2025-05-28'],
        ['DES', 'DDS', '18', 'NAYARIT', '2025-05-28'],
        ['DES', 'DDS', '19', 'NUEVO LEON', '2025-05-28'],  # Sin acento
        ['DES', 'DDS', '20', 'OAXACA', '2025-05-28'],
    ]
    
    # Datos del esquema DB2 (con diferentes abreviaciones y errores)
    estados_db2 = [
        # Algunos con abreviaciones, otros con errores típicos
        ['DES', 'DB2', 'AGS', 'AGUASCALIENTES', '2025-05-28'],
        ['DES', 'DB2', 'BC', 'BAJA CALIFORNIA', '2025-05-28'],
        ['DES', 'DB2', 'BCS', 'BAJA CALIFORNIA SUR', '2025-05-28'],
        ['DES', 'DB2', 'CAM', 'CAMPECHE', '2025-05-28'],
        ['DES', 'DB2', 'COAH', 'COAHUILA DE ZARAGOZA', '2025-05-28'],  # Completo
        ['DES', 'DB2', 'COL', 'COLIMA', '2025-05-28'],
        ['DES', 'DB2', 'CHIS', 'CHIAPAS', '2025-05-28'],
        ['DES', 'DB2', 'CHIH', 'CHIHUAHUA', '2025-05-28'],
        ['DES', 'DB2', 'DF', 'D.F.', '2025-05-28'],  # Abreviación muy vieja
        ['DES', 'DB2', 'DGO', 'DURANGO', '2025-05-28'],
        ['DES', 'DB2', 'GTO', 'GUANAJUATO', '2025-05-28'],
        ['DES', 'DB2', 'GRO', 'GUERRERO', '2025-05-28'],
        ['DES', 'DB2', 'HGO', 'HIDALGO', '2025-05-28'],
        ['DES', 'DB2', 'JAL', 'JALISCO', '2025-05-28'],
        ['DES', 'DB2', 'MEX', 'ESTADO DE MEXICO', '2025-05-28'],  # Diferente formato
        ['DES', 'DB2', 'MICH', 'MICHOACÁN DE OCAMPO', '2025-05-28'],  # Completo
        ['DES', 'DB2', 'MOR', 'MORELOS', '2025-05-28'],
        ['DES', 'DB2', 'NAY', 'NAYARIT', '2025-05-28'],
        ['DES', 'DB2', 'NL', 'NUEVO LEÓN', '2025-05-28'],  # Con acento
        ['DES', 'DB2', 'OAX', 'OAXACA', '2025-05-28'],
        # Agregar algunos datos "basura" para probar la limpieza
        ['DES', 'DB2', 'XXX', 'ESTADO_INEXISTENTE', '2025-05-28'],
        ['DES', 'DB2', '999', 'BASURA123', '2025-05-28'],
        ['DES', 'DB2', '', 'SIN_CLAVE', '2025-05-28'],
    ]
    
    # Crear DataFrames (como tablas de Excel en Python)
    df_dds = pd.DataFrame(estados_dds, columns=[
        'division', 'esquema', 'clave_original', 'nombre_original', 'fecha_extraccion'
    ])
    
    df_db2 = pd.DataFrame(estados_db2, columns=[
        'division', 'esquema', 'clave_original', 'nombre_original', 'fecha_extraccion'
    ])
    
    # Crear la carpeta si no existe
    os.makedirs(PATHS['des_raw'], exist_ok=True)
    
    # Guardar archivos CSV
    archivo_dds = os.path.join(PATHS['des_raw'], FILES['estados_dds'])
    archivo_db2 = os.path.join(PATHS['des_raw'], FILES['estados_db2'])
    
    df_dds.to_csv(archivo_dds, index=False, encoding='utf-8')
    df_db2.to_csv(archivo_db2, index=False, encoding='utf-8')
    
    print(f"✅ Creado: {archivo_dds} ({len(df_dds)} registros)")
    print(f"✅ Creado: {archivo_db2} ({len(df_db2)} registros)")
    
    return df_dds, df_db2

# ========================================
# 2. DATOS DE REFERENCIA - SEPOMEX
# ========================================

def crear_estados_sepomex_referencia():
    """
    💡 Crear el catálogo oficial de estados de SEPOMEX
    Estos son los datos "correctos" contra los que vamos a comparar
    """
    
    print("📚 Creando catálogo de referencia SEPOMEX...")
    
    # Estados oficiales de México según SEPOMEX
    estados_sepomex = [
        # Formato: clave, nombre_oficial, nombre_completo, lat, lng
        ['01', 'AGUASCALIENTES', 'AGUASCALIENTES', 21.8853, -102.2916],
        ['02', 'BAJA CALIFORNIA', 'BAJA CALIFORNIA', 30.8406, -115.2838],
        ['03', 'BAJA CALIFORNIA SUR', 'BAJA CALIFORNIA SUR', 26.0444, -111.6661],
        ['04', 'CAMPECHE', 'CAMPECHE', 19.8301, -90.5349],
        ['05', 'COAHUILA DE ZARAGOZA', 'COAHUILA DE ZARAGOZA', 27.0587, -101.7068],
        ['06', 'COLIMA', 'COLIMA', 19.2452, -103.7240],
        ['07', 'CHIAPAS', 'CHIAPAS', 16.7569, -93.1292],
        ['08', 'CHIHUAHUA', 'CHIHUAHUA', 28.6330, -106.0691],
        ['09', 'CIUDAD DE MÉXICO', 'CIUDAD DE MÉXICO', 19.4326, -99.1332],  # Nombre actual
        ['10', 'DURANGO', 'DURANGO', 24.5594, -104.6591],
        ['11', 'GUANAJUATO', 'GUANAJUATO', 21.0190, -101.2574],
        ['12', 'GUERRERO', 'GUERRERO', 17.4392, -99.5451],
        ['13', 'HIDALGO', 'HIDALGO', 20.0911, -98.7624],
        ['14', 'JALISCO', 'JALISCO', 20.6597, -103.3496],
        ['15', 'MÉXICO', 'ESTADO DE MÉXICO', 19.2808, -99.7559],
        ['16', 'MICHOACÁN DE OCAMPO', 'MICHOACÁN DE OCAMPO', 19.5665, -101.7068],
        ['17', 'MORELOS', 'MORELOS', 18.6813, -99.1013],
        ['18', 'NAYARIT', 'NAYARIT', 21.7514, -104.8455],
        ['19', 'NUEVO LEÓN', 'NUEVO LEÓN', 25.5922, -99.9962],
        ['20', 'OAXACA', 'OAXACA', 17.0732, -96.7266],
        ['21', 'PUEBLA', 'PUEBLA', 19.0414, -98.2063],
        ['22', 'QUERÉTARO', 'QUERÉTARO', 20.5888, -100.3899],
        ['23', 'QUINTANA ROO', 'QUINTANA ROO', 19.1817, -88.4791],
        ['24', 'SAN LUIS POTOSÍ', 'SAN LUIS POTOSÍ', 22.1565, -100.9855],
        ['25', 'SINALOA', 'SINALOA', 25.1721, -107.4795],
        ['26', 'SONORA', 'SONORA', 29.2972, -110.3309],
        ['27', 'TABASCO', 'TABASCO', 17.8409, -92.6189],
        ['28', 'TAMAULIPAS', 'TAMAULIPAS', 24.2669, -98.8363],
        ['29', 'TLAXCALA', 'TLAXCALA', 19.3139, -98.2404],
        ['30', 'VERACRUZ DE IGNACIO DE LA LLAVE', 'VERACRUZ DE IGNACIO DE LA LLAVE', 19.1738, -96.1342],
        ['31', 'YUCATÁN', 'YUCATÁN', 20.7099, -89.0943],
        ['32', 'ZACATECAS', 'ZACATECAS', 22.7709, -102.5832]
    ]
    
    # Crear DataFrame
    df_sep