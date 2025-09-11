Quiero crear un servicio Python (FastAPI) llamado `anomaly-detector` que detecte anomalías en logs y genere explicaciones usando un LLM local (via ollama/llama-cpp).

Requisitos:
1. Debe ser un servicio FastAPI con al menos un endpoint:
   - POST /detect
     - Input: archivo de logs en texto plano o JSON con líneas de log
     - Output: JSON con anomalías detectadas, score de cada una, y explicación en lenguaje natural generada por el LLM.
   - GET /health
     - Devuelve {"status": "ok"} para health check en Docker.

2. La detección de anomalías se hará con **Isolation Forest** sobre features simples extraídas del log (ejemplo: número de palabras, longitud, entropía, presencia de keywords sospechosas como "failed", "error", "unauthorized").
3. Las anomalías detectadas deben pasarse a un LLM corriendo localmente en `ollama-service` (usando el modelo Gemma GGUF).
   - El prompt al LLM debe ser corto y directo, del estilo: 
     "Explica en lenguaje natural por qué este log parece sospechoso: <log_entry>"
4. La respuesta del LLM debe incluirse en el JSON de salida.
5. El resultado final se guardará también en un archivo JSON en `/app/reports/report-{timestamp}.json`.

6. Preparar un `Dockerfile` para este servicio con:
   - Python 3.11
   - Dependencias en requirements.txt: fastapi, uvicorn, scikit-learn, pandas, requests
   - Exponer puerto 8000
   - CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

7. Estructura de directorios:
build/anomaly-detector/Dockerfile
data/anomaly-detector/config/
data/anomaly-detector/scripts/
data/anomaly-detector/tests/
data/anomaly-detector/reports/


8. Generar un ejemplo de `requirements.txt` con fastapi, uvicorn, scikit-learn, pandas y requests.

Quiero ver:
- Un archivo `main.py` con la implementación inicial
- Un archivo `requirements.txt`
- Un `Dockerfile` listo para usarse en la carpeta `build/anomaly-detector/`
👉 Con este prompt en Cursor, te va a generar los tres archivos base directamente (main.py, requirements.txt, Dockerfile) y ya puedes levantar el contenedor con tu docker-compose.yml.