"""
Debug script para FallbackExplanationGenerator
Ejecutar: python -m debug.test_fallback_explanation
"""
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.explanation import FallbackExplanationGenerator

def test_fallback_explanation():
    """Prueba el generador de explicaciones de fallback"""
    generator = FallbackExplanationGenerator()
    
    print("=" * 80)
    print("TEST: FallbackExplanationGenerator")
    print("=" * 80)
    
    test_cases = [
        ("ERROR: Connection timeout occurred", -0.15),
        ("ERROR: Failed to connect to database", -0.2),
        ("ERROR: Out of memory (OOM) detected", -0.25),
        ("ERROR: Disk space exceeded", -0.18),
        ("ERROR: Permission denied accessing file", -0.12),
        ("WARNING: High memory usage detected", -0.08),
        ("INFO: System restart scheduled", -0.05),
        ("CRITICAL: Service unavailable", -0.3),
        ("Anomalía genérica sin palabras clave específicas", -0.1)
    ]
    
    print("\n[TEST] Generación de Explicaciones de Fallback")
    print("-" * 80)
    
    for log_entry, score in test_cases:
        explanation = generator.generate(log_entry, score)
        print(f"\nLog:    {log_entry}")
        print(f"Score:  {score}")
        print(f"Fallback: {explanation}")
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("✅ FallbackExplanationGenerator test completado")
    print("=" * 80)

if __name__ == "__main__":
    test_fallback_explanation()
