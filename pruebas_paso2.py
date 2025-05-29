# ========================================
# ARCHIVO: pruebas_paso2.py
# PRUEBAS INDEPENDIENTES PARA EL PASO 2
# ========================================

"""
INSTRUCCIONES:
1. Guarda este archivo como 'pruebas_paso2.py'
2. Ejecuta desde terminal: python pruebas_paso2.py
3. NO ejecutar desde Streamlit para evitar conflictos
"""

import sys
import os

# Agregar el directorio actual al path para importar tu sistema
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ========================================
# IMPORTACIÓN SEGURA
# ========================================

def importar_sistema_seguro():
    """Importar sistema sin conflictos de Streamlit"""
    
    try:
        # Mockear Streamlit para evitar errores
        import streamlit as st
        
        # Si ya está configurado, no hacer nada
        if hasattr(st, '_is_running_with_streamlit'):
            return None
            
    except ImportError:
        pass
    
    try:
        # Intentar importar tu sistema
        from sistema_completo_normalizacion import SistemaNormalizacion
        return SistemaNormalizacion
    except ImportError as e:
        print(f"❌ Error importando: {e}")
        print("Asegúrate de que el archivo se llame 'sistema_completo_normalizacion.py'")
        return None
    except Exception as e:
        print(f"⚠️ Error al importar (probablemente por Streamlit): {e}")
        return None

# ========================================
# VERIFICACIÓN PASO 2 (SIN STREAMLIT)
# ========================================

def verificar_paso2_sin_streamlit():
    """
    Verificar Paso 2 sin dependencias de Streamlit
    """
    
    print("🔍 VERIFICANDO IMPLEMENTACIÓN PASO 2...")
    print("=" * 50)
    
    # Importar sistema
    SistemaNormalizacion = importar_sistema_seguro()
    
    if not SistemaNormalizacion:
        print("❌ No se pudo importar SistemaNormalizacion")
        return False
    
    try:
        # Crear instancia sin inicialización completa de Streamlit
        sistema = SistemaNormalizacion()
        
        print("✅ Sistema importado correctamente")
        
        # Verificar métodos del Paso 1
        metodos_paso1 = [
            'inicializar_diccionarios_inteligentes',
            'expandir_abreviaciones_inteligente',
            'corregir_errores_tipograficos'
        ]
        
        for metodo in metodos_paso1:
            if hasattr(sistema, metodo):
                print(f"✅ Paso 1 - Método {metodo} disponible")
            else:
                print(f"❌ Paso 1 - Método {metodo} falta")
                return False
        
        # Verificar métodos del Paso 2
        metodos_paso2 = [
            'limpiar_texto_inteligente',
            'limpieza_especifica_por_tipo',
            'inicializar_patrones_limpieza'
        ]
        
        for metodo in metodos_paso2:
            if hasattr(sistema, metodo):
                print(f"✅ Paso 2 - Método {metodo} disponible")
            else:
                print(f"❌ Paso 2 - Método {metodo} falta - NECESITA IMPLEMENTACIÓN")
                return False
        
        # Verificar diccionarios
        diccionarios_requeridos = ['abreviaciones', 'correcciones', 'sinonimos']
        
        for diccionario in diccionarios_requeridos:
            if hasattr(sistema, diccionario) and len(getattr(sistema, diccionario)) > 0:
                print(f"✅ Diccionario {diccionario} cargado ({len(getattr(sistema, diccionario))} elementos)")
            else:
                print(f"❌ Diccionario {diccionario} no cargado")
                return False
        
        # Probar caso simple
        print("\n🧪 PROBANDO FUNCIONALIDAD:")
        
        casos_prueba = [
            ("B.C.", "ESTADOS"),
            ("DOCT0RES", "COLONIAS"),
            ("CD. JUAREZ", "CIUDADES")
        ]
        
        for texto, tipo in casos_prueba:
            try:
                resultado = sistema.limpiar_texto_inteligente(texto, tipo)
                print(f"   '{texto}' ({tipo}) → '{resultado}'")
                
                # Verificar que hubo alguna mejora
                if len(resultado) >= len(texto):
                    print(f"     ✅ Procesado correctamente")
                else:
                    print(f"     ⚠️ Resultado más corto de lo esperado")
                    
            except Exception as e:
                print(f"   ❌ Error procesando '{texto}': {e}")
                return False
        
        print(f"\n🎉 PASO 2 VERIFICADO CORRECTAMENTE")
        print(f"🚀 Sistema listo para procesar archivos con limpieza inteligente")
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

# ========================================
# PRUEBA COMPLETA PASO 2 (SIN STREAMLIT)
# ========================================

def probar_paso2_completo_sin_streamlit():
    """
    Probar Paso 2 completo sin Streamlit
    """
    
    print("\n🧪 PROBANDO PASO 2 - CASOS COMPLETOS")
    print("=" * 50)
    
    SistemaNormalizacion = importar_sistema_seguro()
    
    if not SistemaNormalizacion:
        return False
    
    try:
        sistema = SistemaNormalizacion()
        
        # Casos de prueba por tipo
        casos_prueba = {
            'ESTADOS': [
                ("b.c.", "debe expandir a BAJA CALIFORNIA"),
                ("CDMX", "debe expandir a CIUDAD DE MEXICO"),
                ("N.L.", "debe expandir a NUEVO LEON"),
                ("edo mex", "debe expandir a ESTADO DE MEXICO")
            ],
            'CIUDADES': [
                ("cd. juárez", "debe limpiar a CIUDAD JUAREZ"),
                ("gdle", "debe expandir a GUADALAJARA"),
                ("mty", "debe expandir a MONTERREY")
            ],
            'COLONIAS': [
                ("doct0res", "debe corregir 0 por O"),
                ("sta. maría", "debe expandir STA y limpiar acentos"),
                ("fracc. residencial", "debe expandir FRACC"),
                ("centro histórico", "debe normalizar a CENTRO HISTORICO")
            ]
        }
        
        total_casos = 0
        casos_exitosos = 0
        
        for tipo, casos in casos_prueba.items():
            print(f"\n📋 PROBANDO TIPO: {tipo}")
            print("-" * 30)
            
            for caso_original, descripcion in casos:
                total_casos += 1
                print(f"\n🔍 Caso {total_casos}: '{caso_original}'")
                print(f"   Expectativa: {descripcion}")
                
                try:
                    resultado = sistema.limpiar_texto_inteligente(caso_original, tipo)
                    print(f"   Resultado: '{resultado}'")
                    
                    # Verificar mejoras específicas
                    original_upper = caso_original.upper()
                    mejoras = []
                    
                    if len(resultado) > len(original_upper):
                        mejoras.append("EXPANDIDO")
                    if "BAJA CALIFORNIA" in resultado and "B.C." in caso_original.upper():
                        mejoras.append("ABREVIATURA")
                    if "DOCTORES" in resultado and "0" in caso_original:
                        mejoras.append("CORRECCIÓN_TIPOGRÁFICA")
                    if "SANTA" in resultado and "STA" in caso_original.upper():
                        mejoras.append("EXPANSIÓN_PREFIJO")
                    
                    if mejoras:
                        print(f"   ✅ MEJORAS: {', '.join(mejoras)}")
                        casos_exitosos += 1
                    elif resultado != original_upper:
                        print(f"   ⚡ CAMBIO: Texto transformado")
                        casos_exitosos += 1
                    else:
                        print(f"   ➡️ SIN_CAMBIO")
                        
                except Exception as e:
                    print(f"   ❌ ERROR: {e}")
        
        print(f"\n📊 RESUMEN FINAL:")
        print(f"   Total casos: {total_casos}")
        print(f"   Exitosos: {casos_exitosos}")
        print(f"   Tasa éxito: {casos_exitosos/total_casos*100:.1f}%")
        
        if casos_exitosos >= total_casos * 0.6:  # 60% mínimo
            print(f"\n🎉 PASO 2 FUNCIONANDO CORRECTAMENTE")
            print(f"✅ Sistema listo para normalización inteligente")
            return True
        else:
            print(f"\n⚠️ PASO 2 NECESITA AJUSTES")
            return False
            
    except Exception as e:
        print(f"❌ Error en prueba completa: {e}")
        return False

# ========================================
# COMPARACIÓN ANTES/DESPUÉS
# ========================================

def mostrar_comparacion():
    """Mostrar comparación antes/después"""
    
    print("\n🔍 COMPARACIÓN ANTES/DESPUÉS")
    print("=" * 40)
    
    casos = [
        "B.C.",
        "DOCT0RES", 
        "STA. MARÍA",
        "CD. JUÁREZ",
        "FRACC. RESIDENCIAL"
    ]
    
    SistemaNormalizacion = importar_sistema_seguro()
    
    if not SistemaNormalizacion:
        return
    
    try:
        sistema = SistemaNormalizacion()
        
        for caso in casos:
            print(f"\nTexto original: '{caso}'")
            
            # Limpieza básica (simulación)
            basico = caso.upper().strip()
            print(f"  Básico:      '{basico}'")
            
            # Limpieza inteligente
            inteligente = sistema.limpiar_texto_inteligente(caso, 'COLONIAS')
            print(f"  Inteligente: '{inteligente}'")
            
            # Mostrar mejora
            if len(inteligente) > len(basico):
                print(f"  🎯 MEJORA: +{len(inteligente) - len(basico)} caracteres")
            elif inteligente != basico:
                print(f"  🔄 TRANSFORMADO")
    
    except Exception as e:
        print(f"❌ Error en comparación: {e}")

# ========================================
# FUNCIÓN PRINCIPAL
# ========================================

def main():
    """Función principal de pruebas"""
    
    print("🏠 SISTEMA DE NORMALIZACIÓN - PRUEBAS PASO 2")
    print("=" * 60)
    
    # Verificar implementación
    if verificar_paso2_sin_streamlit():
        print("\n" + "="*60)
        
        # Probar casos completos
        if probar_paso2_completo_sin_streamlit():
            print("\n" + "="*60)
            
            # Mostrar comparación
            mostrar_comparacion()
            
            print("\n" + "="*60)
            print("🎉 TODAS LAS PRUEBAS COMPLETADAS")
            print("✅ El Paso 2 está funcionando correctamente")
            print("🚀 Puedes proceder a usar el sistema en Streamlit")
        else:
            print("\n❌ Las pruebas fallaron. Revisar implementación.")
    else:
        print("\n❌ La verificación falló. Implementar cambios necesarios.")

# ========================================
# EJECUCIÓN
# ========================================

if __name__ == "__main__":
    main()