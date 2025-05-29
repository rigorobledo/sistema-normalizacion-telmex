# ========================================
# SCRIPT SIMPLE PARA CARGAR REFERENCIAS
# ========================================

"""
Script corregido para cargar referencias básicas
Soluciona el error: "cannot access local variable 'text'"
"""

import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy import text

def cargar_referencias_basicas():
    """Cargar referencias básicas para pruebas - VERSION SIMPLE"""
    
    print("🏗️ CARGANDO REFERENCIAS BÁSICAS")
    print("=" * 40)
    
    try:
        # Importar sistema
        from sistema_completo_normalizacion import SistemaNormalizacion
        sistema = SistemaNormalizacion()
        
        if not sistema.engine:
            print("❌ No hay conexión a base de datos")
            return False
        
        print("✅ Conexión a BD establecida")
        
        # Referencias básicas de estados
        referencias_estados = [
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '02', 'nombre_oficial': 'BAJA CALIFORNIA'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '09', 'nombre_oficial': 'CIUDAD DE MEXICO'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '19', 'nombre_oficial': 'NUEVO LEON'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '20', 'nombre_oficial': 'OAXACA'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '24', 'nombre_oficial': 'SAN LUIS POTOSI'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '08', 'nombre_oficial': 'CHIHUAHUA'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '23', 'nombre_oficial': 'QUINTANA ROO'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '12', 'nombre_oficial': 'GUANAJUATO'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '11', 'nombre_oficial': 'ESTADO DE MEXICO'},
            {'tipo_catalogo': 'ESTADOS', 'codigo_oficial': '10', 'nombre_oficial': 'DURANGO'}
        ]
        
        # Referencias básicas de colonias
        referencias_colonias = [
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00001', 'nombre_oficial': 'CENTRO'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00002', 'nombre_oficial': 'DOCTORES'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00003', 'nombre_oficial': 'ROMA NORTE'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00004', 'nombre_oficial': 'SANTA MARIA LA RIBERA'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00005', 'nombre_oficial': 'RESIDENCIAL'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00006', 'nombre_oficial': 'AMPLIACION SANTIAGO'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00007', 'nombre_oficial': 'CENTRO HISTORICO'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00008', 'nombre_oficial': 'LAS FLORES'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00009', 'nombre_oficial': 'ZONA INDUSTRIAL'},
            {'tipo_catalogo': 'COLONIAS', 'codigo_oficial': '00010', 'nombre_oficial': 'UNIDAD HABITACIONAL'}
        ]
        
        # Referencias básicas de ciudades
        referencias_ciudades = [
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '001', 'nombre_oficial': 'AGUASCALIENTES'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '002', 'nombre_oficial': 'CIUDAD JUAREZ'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '003', 'nombre_oficial': 'GUADALAJARA'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '004', 'nombre_oficial': 'MONTERREY'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '005', 'nombre_oficial': 'TIJUANA'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '006', 'nombre_oficial': 'CIUDAD DE MEXICO'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '007', 'nombre_oficial': 'MEXICALI'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '008', 'nombre_oficial': 'CANCUN'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '009', 'nombre_oficial': 'CIUDAD OBREGON'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '010', 'nombre_oficial': 'HERMOSILLO'},
            {'tipo_catalogo': 'CIUDADES', 'codigo_oficial': '011', 'nombre_oficial': 'ORIZABA'}
        ]
        
        # Combinar todas las referencias
        todas_referencias = referencias_estados + referencias_colonias + referencias_ciudades
        
        # Agregar campos requeridos
        for ref in todas_referencias:
            ref['id_referencia'] = str(uuid.uuid4())
            ref['nombre_alternativo'] = None
            ref['coordenadas_lat'] = None
            ref['coordenadas_lng'] = None
            ref['estado_padre'] = None
            ref['municipio_padre'] = None
            ref['activo'] = True
            ref['fecha_actualizacion'] = datetime.now()
        
        print(f"📊 Referencias preparadas:")
        print(f"   Estados: {len(referencias_estados)}")
        print(f"   Colonias: {len(referencias_colonias)}")
        print(f"   Ciudades: {len(referencias_ciudades)}")
        print(f"   Total: {len(todas_referencias)}")
        
        # Limpiar tabla existente
        with sistema.engine.connect() as conn:
            conn.execute(text("DELETE FROM referencias_normalizacion"))
            conn.commit()
            print("🧹 Tabla limpiada")
        
        # Insertar nuevas referencias
        df_referencias = pd.DataFrame(todas_referencias)
        df_referencias.to_sql('referencias_normalizacion', sistema.engine, if_exists='append', index=False)
        
        print("✅ Referencias insertadas")
        
        # Verificar carga
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tipo_catalogo, COUNT(*) as total
                FROM referencias_normalizacion
                GROUP BY tipo_catalogo
                ORDER BY tipo_catalogo
            """))
            
            print("\n📊 VERIFICACIÓN:")
            total_general = 0
            for row in result:
                print(f"   {row[0]}: {row[1]} referencias")
                total_general += row[1]
            
            print(f"   TOTAL: {total_general} referencias")
        
        if total_general > 0:
            print("\n🎉 REFERENCIAS CARGADAS EXITOSAMENTE")
            print("✅ Ahora procesa tus archivos de prueba")
            print("🎯 Deberías ver EXACTO/FUZZY en lugar de SIN_MATCH")
            return True
        else:
            print("\n❌ No se cargaron referencias")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando sistema: {e}")
        print("💡 Asegúrate de que el archivo se llame 'sistema_completo_normalizacion.py'")
        return False
        
    except Exception as e:
        print(f"❌ Error cargando referencias: {e}")
        print(f"💡 Tipo de error: {type(e).__name__}")
        return False

def probar_busqueda_simple():
    """Probar una búsqueda simple"""
    
    print("\n🧪 PROBANDO BÚSQUEDA SIMPLE")
    print("=" * 30)
    
    try:
        from sistema_completo_normalizacion import SistemaNormalizacion
        sistema = SistemaNormalizacion()
        
        # Probar búsqueda directa
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT nombre_oficial, tipo_catalogo
                FROM referencias_normalizacion
                WHERE nombre_oficial LIKE '%BAJA%'
                LIMIT 5
            """))
            
            print("Búsqueda de 'BAJA' en referencias:")
            for row in result:
                print(f"   ✅ {row[0]} ({row[1]})")
    
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

def main():
    """Función principal"""
    
    print("🏠 CARGA SIMPLE DE REFERENCIAS")
    print("=" * 50)
    
    if cargar_referencias_basicas():
        probar_busqueda_simple()
        
        print("\n" + "=" * 50)
        print("🚀 SIGUIENTES PASOS:")
        print("1. Ejecuta tu sistema Streamlit")
        print("2. Procesa los archivos de prueba")
        print("3. Observa los cambios:")
        print("   • b.c. → BAJA CALIFORNIA (EXACTO)")
        print("   • d0ct0res → DOCTORES (FUZZY)")
        print("   • gdle → GUADALAJARA (EXACTO)")
    else:
        print("\n❌ Falló la carga de referencias")

if __name__ == "__main__":
    main()