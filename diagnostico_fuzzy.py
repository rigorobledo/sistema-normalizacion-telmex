# ========================================
# DIAGNÓSTICO Y CORRECCIÓN FUZZY MATCHING
# ========================================

"""
PROBLEMA: Exitosos 0, Confianza N/A
CAUSA: El fuzzy matching no encuentra coincidencias
SOLUCIÓN: Diagnosticar y corregir buscar_en_referencias()
"""

from sqlalchemy import text
import pandas as pd
from fuzzywuzzy import fuzz, process

def diagnosticar_busqueda_referencias():
    """Diagnosticar por qué no funcionan las búsquedas"""
    
    print("🔍 DIAGNÓSTICO DE BÚSQUEDA EN REFERENCIAS")
    print("=" * 50)
    
    try:
        from sistema_completo_normalizacion import SistemaNormalizacion
        sistema = SistemaNormalizacion()
        
        # 1. Verificar que hay referencias cargadas
        print("1. VERIFICANDO REFERENCIAS CARGADAS:")
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tipo_catalogo, COUNT(*) as total
                FROM referencias_normalizacion
                WHERE activo = true
                GROUP BY tipo_catalogo
            """))
            
            for row in result:
                print(f"   ✅ {row[0]}: {row[1]} referencias")
        
        # 2. Probar limpieza de texto
        print("\n2. PROBANDO LIMPIEZA DE TEXTO:")
        casos_limpieza = ["b.c.", "d0ct0res", "gdle"]
        
        for caso in casos_limpieza:
            if hasattr(sistema, 'limpiar_texto_inteligente'):
                resultado = sistema.limpiar_texto_inteligente(caso, 'ESTADOS')
                print(f"   '{caso}' → '{resultado}'")
            else:
                print(f"   ❌ Método limpiar_texto_inteligente no encontrado")
        
        # 3. Probar búsqueda directa
        print("\n3. PROBANDO BÚSQUEDA DIRECTA:")
        
        # Buscar "BAJA CALIFORNIA" directamente
        resultado = sistema.buscar_en_referencias("BAJA CALIFORNIA", "ESTADOS")
        if resultado:
            print(f"   ✅ 'BAJA CALIFORNIA' encontrada: {resultado['metodo']} ({resultado['confianza']})")
        else:
            print(f"   ❌ 'BAJA CALIFORNIA' NO encontrada")
        
        # 4. Revisar el método buscar_en_referencias
        print("\n4. ANALIZANDO MÉTODO buscar_en_referencias:")
        print("   Método actual en tu sistema:")
        
        # Obtener referencias manualmente para probar
        with sistema.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT nombre_oficial FROM referencias_normalizacion 
                WHERE tipo_catalogo = 'ESTADOS' AND activo = true
                LIMIT 5
            """))
            
            nombres_ref = [row[0] for row in result]
            print(f"   Referencias disponibles: {nombres_ref}")
        
        # 5. Probar fuzzy matching manual
        print("\n5. PROBANDO FUZZY MATCHING MANUAL:")
        
        texto_buscar = "BAJA CALIFORNIA"
        if nombres_ref:
            mejor_match = process.extractOne(texto_buscar, nombres_ref, scorer=fuzz.token_sort_ratio)
            print(f"   Texto: '{texto_buscar}'")
            print(f"   Mejor match: {mejor_match}")
            
            # Probar con texto procesado
            texto_procesado = sistema.limpiar_texto_inteligente("b.c.", "ESTADOS")
            mejor_match2 = process.extractOne(texto_procesado, nombres_ref, scorer=fuzz.token_sort_ratio)
            print(f"   Texto procesado: '{texto_procesado}'")
            print(f"   Mejor match: {mejor_match2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en diagnóstico: {e}")
        return False

def corregir_buscar_en_referencias():
    """Método corregido para buscar_en_referencias"""
    
    codigo_corregido = '''
def buscar_en_referencias(self, texto_limpio, tipo_catalogo):
    """Buscar coincidencias en las referencias usando IA - VERSIÓN CORREGIDA"""
    
    print(f"🔍 Buscando: '{texto_limpio}' en {tipo_catalogo}")
    
    try:
        with self.engine.connect() as conn:
            # Obtener referencias del tipo correspondiente
            result = conn.execute(text("""
                SELECT * FROM referencias_normalizacion 
                WHERE tipo_catalogo = :tipo AND activo = true
            """), {'tipo': tipo_catalogo})
            
            referencias = []
            for row in result:
                referencias.append(dict(row._mapping))
        
        if not referencias:
            print(f"   ❌ No hay referencias para {tipo_catalogo}")
            return None
        
        print(f"   📊 Encontradas {len(referencias)} referencias para {tipo_catalogo}")
        
        # Buscar coincidencia exacta
        for ref in referencias:
            nombre_ref_limpio = ref['nombre_oficial'].upper().strip()
            if texto_limpio == nombre_ref_limpio:
                print(f"   ✅ EXACTO: '{texto_limpio}' = '{nombre_ref_limpio}'")
                return {
                    **ref,
                    'metodo': 'EXACTO',
                    'confianza': 1.0
                }
        
        # Buscar con fuzzy matching - CORREGIDO
        nombres_referencias = [ref['nombre_oficial'].upper().strip() for ref in referencias]
        
        print(f"   🔍 Fuzzy: comparando '{texto_limpio}' con {len(nombres_referencias)} nombres")
        
        # Probar diferentes scorers
        mejor_fuzzy = process.extractOne(texto_limpio, nombres_referencias, scorer=fuzz.token_sort_ratio)
        
        print(f"   🎯 Mejor fuzzy: {mejor_fuzzy}")
        
        if mejor_fuzzy and mejor_fuzzy[1] >= 60:  # Umbral mínimo 60%
            # Encontrar la referencia correspondiente
            for ref in referencias:
                nombre_ref = ref['nombre_oficial'].upper().strip()
                if nombre_ref == mejor_fuzzy[0]:
                    print(f"   ✅ FUZZY: '{texto_limpio}' → '{nombre_ref}' ({mejor_fuzzy[1]}%)")
                    return {
                        **ref,
                        'metodo': 'FUZZY_ALTO' if mejor_fuzzy[1] >= 80 else 'FUZZY_BAJO',
                        'confianza': mejor_fuzzy[1] / 100.0
                    }
        
        print(f"   ❌ Sin coincidencias para '{texto_limpio}'")
        return None
        
    except Exception as e:
        print(f"   ❌ Error buscando referencias: {e}")
        return None
    '''
    
    print("🔧 MÉTODO CORREGIDO:")
    print("="*50)
    print(codigo_corregido)

def probar_normalizacion_completa():
    """Probar el proceso completo de normalización"""
    
    print("\n🧪 PROBANDO NORMALIZACIÓN COMPLETA")
    print("=" * 40)
    
    try:
        from sistema_completo_normalizacion import SistemaNormalizacion
        sistema = SistemaNormalizacion()
        
        casos_prueba = [
            ("b.c.", "ESTADOS"),
            ("d0ct0res", "COLONIAS"), 
            ("gdle", "CIUDADES")
        ]
        
        for texto_original, tipo in casos_prueba:
            print(f"\n🔍 Procesando: '{texto_original}' ({tipo})")
            
            # Paso 1: Limpiar texto
            if hasattr(sistema, 'limpiar_texto_inteligente'):
                texto_limpio = sistema.limpiar_texto_inteligente(texto_original, tipo)
                print(f"   Texto limpio: '{texto_limpio}'")
            else:
                texto_limpio = texto_original.upper()
                print(f"   Texto básico: '{texto_limpio}'")
            
            # Paso 2: Buscar referencias
            resultado = sistema.buscar_en_referencias(texto_limpio, tipo)
            
            if resultado:
                print(f"   ✅ Encontrado: {resultado['nombre_oficial']} ({resultado['metodo']} - {resultado['confianza']:.1%})")
            else:
                print(f"   ❌ No encontrado")
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

def verificar_fuzzywuzzy():
    """Verificar que fuzzywuzzy está funcionando"""
    
    print("\n🔧 VERIFICANDO FUZZYWUZZY")
    print("=" * 30)
    
    try:
        from fuzzywuzzy import fuzz, process
        
        # Prueba simple
        texto1 = "BAJA CALIFORNIA"
        texto2 = "BAJA CALIFORNIA"
        
        ratio = fuzz.ratio(texto1, texto2)
        print(f"Ratio exacto: {ratio}%")
        
        # Prueba con error
        texto3 = "BAJA CAL1FORN1A"
        ratio2 = fuzz.token_sort_ratio(texto1, texto3)
        print(f"Ratio con errores: {ratio2}%")
        
        # Prueba con lista
        opciones = ["BAJA CALIFORNIA", "CALIFORNIA", "BAJA CALIFORNIA SUR"]
        mejor = process.extractOne("BAJA CALIFORNIA", opciones)
        print(f"Mejor de lista: {mejor}")
        
        print("✅ FuzzyWuzzy funcionando correctamente")
        
    except ImportError:
        print("❌ FuzzyWuzzy no está instalado")
        print("Instalar con: pip install fuzzywuzzy python-Levenshtein")
    except Exception as e:
        print(f"❌ Error con FuzzyWuzzy: {e}")

def main():
    """Función principal de diagnóstico"""
    
    print("🏠 DIAGNÓSTICO COMPLETO - FUZZY MATCHING")
    print("=" * 60)
    
    # Verificar fuzzywuzzy
    verificar_fuzzywuzzy()
    
    # Diagnosticar búsquedas
    if diagnosticar_busqueda_referencias():
        
        # Mostrar método corregido
        corregir_buscar_en_referencias()
        
        # Probar normalización
        probar_normalizacion_completa()
        
        print("\n" + "=" * 60)
        print("🎯 SOLUCIONES POSIBLES:")
        print("1. Reemplazar método buscar_en_referencias() con versión corregida")
        print("2. Verificar que limpiar_texto_inteligente() esté funcionando")
        print("3. Instalar fuzzywuzzy si no está disponible")
        print("4. Reducir umbral de fuzzy matching de 60% a 50%")
        
    else:
        print("\n❌ Error en diagnóstico - revisar configuración")

if __name__ == "__main__":
    main()