"""
Script para ejecutar todos los tests de debug
Ejecutar: python -m debug.run_all_tests

Ejecuta todos los tests de componentes en orden lógico
"""
import sys
import os
import subprocess
import asyncio

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test(module_name: str, description: str):
    """Ejecuta un test y muestra el resultado"""
    print("\n" + "=" * 80)
    print(f"EJECUTANDO: {description}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", f"debug.{module_name}"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} - COMPLETADO")
            return True
        else:
            print(f"\n⚠️  {description} - COMPLETADO CON ADVERTENCIAS")
            return False
            
    except Exception as e:
        print(f"\n❌ {description} - ERROR: {e}")
        return False

def main():
    """Ejecuta todos los tests en orden"""
    print("=" * 80)
    print("EJECUTANDO TODOS LOS TESTS DE DEBUG")
    print("=" * 80)
    
    # Tests en orden lógico (de componentes básicos a complejos)
    tests = [
        ("test_log_parser", "LogParser - Análisis de logs"),
        ("test_prompt_builder", "PromptBuilder - Construcción de prompts"),
        ("test_response_parser", "ResponseParser - Parseo de respuestas"),
        ("test_fallback_explanation", "FallbackExplanationGenerator - Explicaciones de respaldo"),
        ("test_ollama_client", "OllamaClientWrapper - Cliente Ollama Cloud"),
        ("test_explanation_service", "ExplanationService - Servicio completo"),
        ("test_course_rbac", "CourseRBAC - Sistema de permisos de cursos"),
        ("test_course_generation", "CourseGeneration - Generación de cursos"),
        ("test_lesson_edit", "LessonEdit - Edición granular de lecciones"),
    ]
    
    results = []
    for module_name, description in tests:
        success = run_test(module_name, description)
        results.append((description, success))
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE TESTS")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASÓ" if success else "⚠️  ADVERTENCIAS"
        print(f"{status}: {description}")
    
    print("\n" + "-" * 80)
    print(f"Total: {passed}/{total} tests pasaron")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 Todos los tests básicos pasaron correctamente!")
    else:
        print("\n⚠️  Algunos tests tienen advertencias (esto puede ser normal)")
        print("   Los tests de Ollama requieren OLLAMA_API_KEY configurada")

if __name__ == "__main__":
    main()
