# Debug de Componentes

> **NOTA**: La documentación completa está en `doc/debug_readme.md`

Esta carpeta contiene scripts de debug para probar cada componente del sistema de explicaciones de forma independiente.

## Estructura

- `test_log_parser.py` - Prueba el parser de logs
- `test_prompt_builder.py` - Prueba el constructor de prompts
- `test_response_parser.py` - Prueba el parser de respuestas
- `test_fallback_explanation.py` - Prueba el generador de fallback
- `test_ollama_client.py` - Prueba el cliente de Ollama Cloud
- `test_explanation_service.py` - Prueba el servicio completo
- `run_all_tests.py` - Ejecuta todos los tests en orden

## Uso

### Ejecutar un test individual

```bash
# Desde la raíz del proyecto
python -m debug.test_log_parser
python -m debug.test_prompt_builder
python -m debug.test_response_parser
python -m debug.test_fallback_explanation
python -m debug.test_ollama_client
python -m debug.test_explanation_service
```

### Ejecutar todos los tests

```bash
python -m debug.run_all_tests
```

## Requisitos

### Tests básicos (sin LLM)
- No requieren configuración adicional
- Funcionan sin conexión a internet
- Incluyen: LogParser, PromptBuilder, ResponseParser, FallbackExplanationGenerator

### Tests con LLM
- Requieren `OLLAMA_API_KEY` configurada en `.env` o variables de entorno
- Requieren conexión a internet
- Incluyen: OllamaClientWrapper, ExplanationService (con LLM)

### Obtener API Key de Ollama Cloud

1. Visita: https://ollama.com/settings/keys
2. Crea una nueva API key
3. Agrega a tu `.env`:
   ```
   OLLAMA_API_KEY=tu_api_key_aqui
   ```

## Notas

- Los tests están diseñados para ejecutarse independientemente
- Si un componente falla, los demás tests continúan ejecutándose
- Los tests con LLM usarán modo fallback automáticamente si no hay API key
- Todos los tests muestran información detallada de lo que están probando

## Orden recomendado de ejecución

1. `test_log_parser.py` - Componente más básico
2. `test_prompt_builder.py` - Depende de LogParser
3. `test_response_parser.py` - Independiente
4. `test_fallback_explanation.py` - Independiente
5. `test_ollama_client.py` - Requiere API key
6. `test_explanation_service.py` - Integra todos los componentes
