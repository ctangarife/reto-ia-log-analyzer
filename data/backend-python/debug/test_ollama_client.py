"""
Debug script para OllamaClientWrapper
Ejecutar: python -m debug.test_ollama_client

NOTA: Requiere OLLAMA_API_KEY configurada en variables de entorno o .env
"""
import sys
import os
import asyncio

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm import OllamaClientWrapper

async def test_ollama_client():
    """Prueba el cliente de Ollama Cloud"""
    print("=" * 80)
    print("TEST: OllamaClientWrapper")
    print("=" * 80)
    
    try:
        # Verificar que OLLAMA_API_KEY esté configurada
        api_key = os.getenv("OLLAMA_API_KEY")
        if not api_key:
            print("\n❌ ERROR: OLLAMA_API_KEY no está configurada")
            print("   Configúrala en .env o como variable de entorno")
            print("   Obtén tu API key en: https://ollama.com/settings/keys")
            return
        
        print(f"\n✅ OLLAMA_API_KEY encontrada: {api_key[:10]}...")
        
        # Crear cliente
        print("\n[TEST 1] Creación del Cliente")
        print("-" * 80)
        client = OllamaClientWrapper()
        print(f"Base URL: {client.base_url}")
        print(f"Modelo:   {client.default_model}")
        print(f"Timeout:  {client.timeout}s")
        
        # Verificar disponibilidad
        print("\n[TEST 2] Verificación de Disponibilidad")
        print("-" * 80)
        available = await client.check_available()
        if available:
            print("✅ Cliente disponible y modelo accesible")
        else:
            print("⚠️  Cliente no disponible o modelo no encontrado")
            print("   Continuando con pruebas básicas...")
        
        # Test de generación simple
        print("\n[TEST 3] Generación de Respuesta Simple")
        print("-" * 80)
        try:
            prompt = "Explica brevemente qué es un log de sistema en una oración."
            print(f"Prompt: {prompt}")
            print("Generando respuesta...")
            
            response = await client.generate_response(
                prompt=prompt,
                temperature=0.7,
                max_tokens=50
            )
            
            print(f"\n✅ Respuesta recibida ({len(response)} caracteres):")
            print(f"   {response}")
            
        except Exception as e:
            print(f"❌ Error generando respuesta: {e}")
            print("   Esto puede ser normal si el modelo no está disponible")
        
        # Test de streaming
        print("\n[TEST 4] Generación de Respuesta en Streaming")
        print("-" * 80)
        try:
            prompt_streaming = "Explica qué es un log de sistema en 3 puntos breves."
            print(f"Prompt: {prompt_streaming}")
            print("\n📡 Respuesta en streaming (chunks en tiempo real):")
            print("-" * 80)
            
            full_response = ""
            chunk_count = 0
            
            async for chunk in client.generate_response_streaming(
                prompt=prompt_streaming,
                temperature=0.7,
                max_tokens=100
            ):
                print(chunk, end="", flush=True)
                full_response += chunk
                chunk_count += 1
            
            print("\n" + "-" * 80)
            print(f"\n✅ Streaming completado:")
            print(f"   - Chunks recibidos: {chunk_count}")
            print(f"   - Total caracteres: {len(full_response)}")
            if len(full_response) > 100:
                print(f"   - Respuesta completa: {full_response[:100]}...")
            else:
                print(f"   - Respuesta completa: {full_response}")
            
        except Exception as e:
            print(f"❌ Error en streaming: {e}")
            print("   Esto puede ser normal si el modelo no está disponible")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("✅ OllamaClientWrapper test completado")
        print("=" * 80)
        
    except ValueError as e:
        print(f"\n❌ ERROR de configuración: {e}")
        print("   Asegúrate de tener OLLAMA_API_KEY configurada")
    except ImportError as e:
        print(f"\n❌ ERROR de importación: {e}")
        print("   Instala ollama-client-lib: pip install ollama-client-lib")
    except Exception as e:
        print(f"\n❌ ERROR inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ollama_client())
