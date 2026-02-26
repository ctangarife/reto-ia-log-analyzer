"""
Debug script para ResponseParser
Ejecutar: python -m debug.test_response_parser
"""
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.explanation import ResponseParser

def test_response_parser():
    """Prueba el parser de respuestas con diferentes formatos"""
    parser = ResponseParser()
    
    print("=" * 80)
    print("TEST: ResponseParser")
    print("=" * 80)
    
    # Test 1: Limpieza de respuesta individual
    print("\n[TEST 1] Limpieza de Respuesta Individual")
    print("-" * 80)
    test_responses = [
        "Problema: El servidor web no puede comunicarse con la base de datos",
        "Impacto: Los usuarios no podrán acceder a la aplicación",
        "Solución: Verificar que la base de datos esté funcionando",
        "Análisis: Se detectó un problema de conectividad",
        "El problema es: Timeout en la conexión",
        "   : Respuesta con espacios y caracteres especiales",
        "Respuesta normal sin prefijos"
    ]
    
    for response in test_responses:
        cleaned = parser.clean_response(response)
        print(f"Original:  {response}")
        print(f"Limpio:    {cleaned}")
        print()
    
    # Test 2: Parseo de respuesta batch
    print("\n[TEST 2] Parseo de Respuesta Batch")
    print("-" * 80)
    batch_response = """ANOMALÍA 1: El servidor web está experimentando timeouts de conexión
ANOMALÍA 2: Se detectó alto uso de memoria que puede causar fallos
ANOMALÍA 3: El disco está lleno y puede impedir guardar archivos"""
    
    explanations = parser.parse_batch_response(batch_response, expected_count=3)
    print(f"Respuesta batch original ({len(batch_response)} caracteres):")
    print(batch_response)
    print(f"\nExplicaciones parseadas ({len(explanations)}):")
    for i, exp in enumerate(explanations, 1):
        print(f"  {i}. {exp}")
    
    # Test 3: Respuesta con formato alternativo
    print("\n[TEST 3] Respuesta con Formato Alternativo")
    print("-" * 80)
    alt_response = """ANOMALÍA 1 Problema de conectividad detectado
ANOMALÍA 2 Error en la base de datos
Línea técnica con información relevante sobre el servidor"""
    
    explanations = parser.parse_batch_response(alt_response, expected_count=3)
    print(f"Respuesta alternativa:")
    print(alt_response)
    print(f"\nExplicaciones parseadas ({len(explanations)}):")
    for i, exp in enumerate(explanations, 1):
        print(f"  {i}. {exp}")
    
    print("\n" + "=" * 80)
    print("✅ ResponseParser test completado")
    print("=" * 80)

if __name__ == "__main__":
    test_response_parser()
