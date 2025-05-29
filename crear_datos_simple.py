# ========================================
# ARCHIVO: crear_datos_simple.py
# VERSIÓN SÚPER SIMPLIFICADA PARA PRINCIPIANTES
# ========================================

print("🚀 INICIANDO creación de datos...")

# ========================================
# IMPORTAR LIBRERÍAS
# ========================================

try:
    import pandas as pd
    import os
    print("✅ Librerías importadas correctamente")
except Exception as e:
    print(f"❌ Error importando librerías: {e}")
    exit()

# ========================================
# CREAR CARPETAS MANUALMENTE
# ========================================

print("\n📁 Creando carpetas...")

carpetas = [
    "data",
    "data/raw", 
    "data/raw/DES",
    "data/reference",
    "data/reference/sepomex",
    "data/processed"
]

for carpeta in carpetas:
    try:
        os.makedirs(carpeta, exist_ok=True)
        print(f"   ✅ {carpeta}")
    except Exception as e:
        print(f"   ❌ Error con {carpeta}: {e}")

# ========================================
# CREAR DATOS AS400 - DDS
# ========================================

print("\n📝 Creando datos AS400-DDS...")

try:
    datos_dds = [
        ['DES', 'DDS', '01', 'AGUASCALIENTES', '2025-05-28'],
        ['DES', 'DDS', '02', 'BAJA CALIFORNIA', '2025-05-28'],
        ['DES', 'DDS', '03', 'BAJA CALIFORNIA SUR', '2025-05-28'],
        ['DES', 'DDS', '09', 'DISTRITO FEDERAL', '2025-05-28'],
        ['DES', 'DDS', '15', 'EDO DE MEXICO', '2025-05-28'],
        ['DES', 'DDS', '16', 'MICHOACAN', '2025-05-28'],
        ['DES', 'DDS', '19', 'NUEVO LEON', '2025-05-28']
    ]
    
    df_dds = pd.DataFrame(datos_dds, columns=[
        'division', 'esquema', 'clave_original', 'nombre_original', 'fecha_extraccion'
    ])
    
    archivo_dds = "data/raw/DES/estados_dds.csv"
    df_dds.to_csv(archivo_dds, index=False, encoding='utf-8')
    
    print(f"   ✅ Creado: {archivo_dds} ({len(df_dds)} registros)")

except Exception as e:
    print(f"   ❌ Error creando DDS: {e}")

# ========================================
# CREAR DATOS AS400 - DB2
# ========================================

print("\n📝 Creando datos AS400-DB2...")

try:
    datos_db2 = [
        ['DES', 'DB2', 'AGS', 'AGUASCALIENTES', '2025-05-28'],
        ['DES', 'DB2', 'BC', 'BAJA CALIFORNIA', '2025-05-28'],
        ['DES', 'DB2', 'BCS', 'BAJA CALIFORNIA SUR', '2025-05-28'],
        ['DES', 'DB2', 'DF', 'D.F.', '2025-05-28'],
        ['DES', 'DB2', 'MEX', 'ESTADO DE MEXICO', '2025-05-28'],
        ['DES', 'DB2', 'MICH', 'MICHOACÁN DE OCAMPO', '2025-05-28'],
        ['DES', 'DB2', 'NL', 'NUEVO LEÓN', '2025-05-28']
    ]
    
    df_db2 = pd.DataFrame(datos_db2, columns=[
        'division', 'esquema', 'clave_original', 'nombre_original', 'fecha_extraccion'
    ])
    
    archivo_db2 = "data/raw/DES/estados_db2.csv"
    df_db2.to_csv(archivo_db2, index=False, encoding='utf-8')
    
    print(f"   ✅ Creado: {archivo_db2} ({len(df_db2)} registros)")

except Exception as e:
    print(f"   ❌ Error creando DB2: {e}")

# ========================================
# CREAR DATOS SEPOMEX
# ========================================

print("\n📚 Creando datos SEPOMEX...")

try:
    datos_sepomex = [
        ['01', 'AGUASCALIENTES', 21.8853, -102.2916],
        ['02', 'BAJA CALIFORNIA', 30.8406, -115.2838],
        ['03', 'BAJA CALIFORNIA SUR', 26.0444, -111.6661],
        ['09', 'CIUDAD DE MÉXICO', 19.4326, -99.1332],
        ['15', 'MÉXICO', 19.2808, -99.7559],
        ['16', 'MICHOACÁN DE OCAMPO', 19.5665, -101.7068],
        ['19', 'NUEVO LEÓN', 25.5922, -99.9962]
    ]
    
    df_sepomex = pd.DataFrame(datos_sepomex, columns=[
        'clave_sepomex', 'nombre_oficial', 'coordenadas_lat', 'coordenadas_lng'
    ])
    
    archivo_sepomex = "data/reference/sepomex/estados_sepomex.csv"
    df_sepomex.to_csv(archivo_sepomex, index=False, encoding='utf-8')
    
    print(f"   ✅ Creado: {archivo_sepomex} ({len(df_sepomex)} registros)")

except Exception as e:
    print(f"   ❌ Error creando SEPOMEX: {e}")

# ========================================
# VERIFICAR ARCHIVOS CREADOS
# ========================================

print("\n🔍 Verificando archivos creados...")

archivos_verificar = [
    "data/raw/DES/estados_dds.csv",
    "data/raw/DES/estados_db2.csv", 
    "data/reference/sepomex/estados_sepomex.csv"
]

todos_ok = True

for archivo in archivos_verificar:
    if os.path.exists(archivo):
        try:
            df_test = pd.read_csv(archivo)
            print(f"   ✅ {archivo} ({len(df_test)} filas)")
        except Exception as e:
            print(f"   ⚠️  {archivo} existe pero hay error leyéndolo: {e}")
            todos_ok = False
    else:
        print(f"   ❌ {archivo} NO EXISTE")
        todos_ok = False

# ========================================
# MOSTRAR EJEMPLOS
# ========================================

if todos_ok:
    print("\n👀 EJEMPLOS DE DATOS CREADOS:")
    print("=" * 40)
    
    try:
        # Mostrar datos AS400
        df_dds = pd.read_csv("data/raw/DES/estados_dds.csv")
        print("\n📄 DATOS AS400-DDS (primeros 3):")
        print(df_dds.head(3).to_string(index=False))
        
        # Mostrar datos SEPOMEX
        df_sep = pd.read_csv("data/reference/sepomex/estados_sepomex.csv")
        print("\n📚 DATOS SEPOMEX (primeros 3):")
        print(df_sep.head(3).to_string(index=False))
        
        print("\n💡 FÍJATE EN LAS DIFERENCIAS:")
        print("   AS400: 'DISTRITO FEDERAL' vs SEPOMEX: 'CIUDAD DE MÉXICO'")
        print("   AS400: 'EDO DE MEXICO' vs SEPOMEX: 'MÉXICO'") 
        print("   AS400: 'MICHOACAN' vs SEPOMEX: 'MICHOACÁN DE OCAMPO'")
        
    except Exception as e:
        print(f"❌ Error mostrando ejemplos: {e}")

# ========================================
# RESUMEN FINAL
# ========================================

print(f"\n🎉 PROCESO COMPLETADO!")
print("=" * 40)

if todos_ok:
    print("✅ Todos los archivos creados correctamente")
    print("🚀 Próximo paso: Crear el algoritmo de normalización")
    print("\n📋 ARCHIVOS LISTOS:")
    for archivo in archivos_verificar:
        print(f"   • {archivo}")
else:
    print("⚠️  Algunos archivos tuvieron problemas")
    print("💡 Revisa los errores arriba")

print("\n🎯 Para continuar:")
print("1. Verifica que todos los archivos existan")
print("2. Abre los archivos CSV para ver los datos")
print("3. Estaremos listos para el algoritmo de normalización")