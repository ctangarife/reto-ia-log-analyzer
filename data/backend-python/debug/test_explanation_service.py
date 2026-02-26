"""
Debug script para ExplanationService completo
Ejecutar: python -m debug.test_explanation_service

NOTA: Requiere OLLAMA_API_KEY configurada para pruebas completas con LLM
      Si no está configurada, solo probará el modo fallback
"""
import sys
import os
import asyncio

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.explanation_service import ExplanationService
from services.llm import OllamaClientWrapper
from services.log_analysis import LogParser
from services.prompts import PromptBuilder
from services.explanation import ResponseParser, FallbackExplanationGenerator

async def test_explanation_service():
    """Prueba el servicio de explicaciones completo"""
    print("=" * 80)
    print("TEST: ExplanationService Completo")
    print("=" * 80)
    
    # Verificar si hay API key para usar LLM real
    has_api_key = bool(os.getenv("OLLAMA_API_KEY"))
    
    if has_api_key:
        print("\n✅ OLLAMA_API_KEY encontrada - Usando LLM real")
        print("   (Si falla, se usará modo fallback automáticamente)")
    else:
        print("\n⚠️  OLLAMA_API_KEY no encontrada - Solo modo fallback")
        print("   Para pruebas completas, configura OLLAMA_API_KEY en .env")
    
    # Crear servicio con componentes personalizados (opcional)
    try:
        llm_client = OllamaClientWrapper() if has_api_key else None
    except (ValueError, ImportError):
        llm_client = None
        print("   Cliente LLM no disponible, usando solo fallback")
    
    service = ExplanationService(
        llm_client=llm_client,
        log_parser=LogParser(),
        prompt_builder=PromptBuilder(),
        response_parser=ResponseParser(),
        fallback_generator=FallbackExplanationGenerator()
    )
    
    # Test 1: Explicación individual
    print("\n[TEST 1] Explicación Individual")
    print("-" * 80)
    test_logs = [
        ("ERROR: Connection timeout from 192.168.1.100", -0.15),
        ("WARNING: High memory usage detected (85%)", -0.08),
        ("CRITICAL: Disk space exceeded on /var/log", -0.25),
        ("ERROR: Permission denied accessing /etc/config", -0.12)
    ]
    
    for log_entry, score in test_logs:
        print(f"\nLog:   {log_entry}")
        print(f"Score: {score}")
        print("Generando explicación...")
        
        try:
            explanation = await service.get_llm_explanation(log_entry, score)
            print(f"✅ Explicación: {explanation}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 2: Batch de explicaciones
    print("\n[TEST 2] Batch de Explicaciones")
    print("-" * 80)
    anomaly_batch = [
        ("ERROR: Database connection failed", -0.2),
        ("WARNING: Slow query detected (>5s)", -0.1),
        ("ERROR: Authentication failed for user admin", -0.18)
    ]
    
    print(f"Procesando batch de {len(anomaly_batch)} anomalías...")
    try:
        explanations = await service.get_batch_explanations(anomaly_batch)
        print(f"\n✅ Explicaciones generadas ({len(explanations)}):")
        for i, exp in enumerate(explanations, 1):
            print(f"  {i}. {exp[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Verificación de disponibilidad
    print("\n[TEST 3] Verificación de Disponibilidad del LLM")
    print("-" * 80)
    if service.llm_client:
        try:
            available = await service.check_llm_available()
            if available:
                print("✅ LLM disponible y funcionando")
            else:
                print("⚠️  LLM no disponible - usando fallback")
        except Exception as e:
            print(f"⚠️  Error verificando disponibilidad: {e}")
    else:
        print("ℹ️  Cliente LLM no configurado - solo modo fallback disponible")
    
    print("\n" + "=" * 80)
    print("✅ ExplanationService test completado")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_explanation_service())
