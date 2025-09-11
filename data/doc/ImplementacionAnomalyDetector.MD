# 🚀 Implementación del Servicio Anomaly Detector

## 📋 Resumen del Proyecto

Se ha implementado exitosamente el servicio `anomaly-detector` para detectar anomalías en logs usando Isolation Forest y generar explicaciones con un LLM local (Ollama/Gemma).

## 🏗️ Arquitectura Implementada

### Estructura de Directorios
```
logsanomaly/
├── 🔨 build/
│   └── 📁 anomaly-detector/
│       └── 📄 Dockerfile
├── 📊 data/
│   ├── 📁 anomaly-detector/
│   │   ├── 📄 main.py
│   │   ├── 📄 requirements.txt
│   │   ├── 📁 config/
│   │   │   └── 📄 config.yml
│   │   ├── 📁 scripts/
│   │   │   └── 📄 test_service.sh
│   │   ├── 📁 tests/
│   │   │   └── 📄 test_anomaly_detection.py
│   │   └── 📁 reports/
│   └── 📁 models/
│       └── 📁 ollama/
├── 🐳 docker-compose.yml
└── 📁 bd/
```

## 🔧 Componentes Implementados

### 1. Servicio FastAPI (`main.py`)
- **Endpoints implementados:**
  - `GET /health` - Health check
  - `POST /detect` - Detección desde archivo
  - `POST /detect-text` - Detección desde JSON

### 2. Detección de Anomalías
- **Algoritmo:** Isolation Forest de scikit-learn
- **Características extraídas:**
  - Longitud del log
  - Número de palabras
  - Entropía del texto
  - Presencia de palabras clave sospechosas
  - Número de caracteres especiales
  - Número de números
  - Longitud promedio de palabras

### 3. Integración con LLM
- **Servicio:** Ollama con modelo Nidum-Gemma-2B-Uncensored-GGUF
- **Prompt:** "Explica en lenguaje natural por qué este log parece sospechoso: {log_entry}"
- **Configuración:** Temperatura 0.7, máximo 150 tokens
- **Soporte GPU:** NVIDIA GPU con 16GB de memoria reservada
- **Cuantización:** Q4_K_M (7.77 GB) para balance óptimo entre rendimiento y memoria

### 4. Generación de Reportes
- **Formato:** JSON con timestamp
- **Ubicación:** `/app/reports/report-{timestamp}.json`
- **Contenido:** Logs analizados, anomalías detectadas, explicaciones

## 🐳 Configuración Docker

### Dockerfile
- **Imagen base:** Python 3.11-slim
- **Puerto:** 8000
- **Dependencias:** FastAPI, scikit-learn, pandas, requests

### Docker Compose
- **Servicios:**
  - `anomaly-detector`: Servicio principal
  - `ollama-service`: LLM local con soporte GPU
- **Red:** `logs_anomaly_net` con aliases
- **Volúmenes:** Código, reportes, modelos
- **GPU:** Reserva de 16GB de memoria y acceso a todas las GPUs NVIDIA

## 📊 Funcionalidades

### Detección de Anomalías
1. **Entrada:** Archivo de logs o JSON con logs
2. **Procesamiento:** Extracción de características
3. **Análisis:** Isolation Forest para detectar outliers
4. **Explicación:** LLM genera explicación para cada anomalía
5. **Salida:** JSON con resultados y reporte guardado

### Palabras Clave Sospechosas
- error, failed, unauthorized, exception
- timeout, denied, critical, fatal
- panic, abort

## 🧪 Testing

### Scripts de Prueba
- **`test_service.sh`:** Pruebas de integración
- **`test_anomaly_detection.py`:** Pruebas unitarias con pytest

### Casos de Prueba
- Health check
- Extracción de características
- Detección de anomalías
- Endpoints con archivo y JSON
- Manejo de errores

## 🚀 Uso del Servicio

### 1. Levantar los Servicios
```bash
docker-compose up -d
```

### 2. Verificar Health Check
```bash
curl http://localhost:8000/health
```

### 3. Detectar Anomalías desde Archivo
```bash
curl -X POST "http://localhost:8000/detect" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@logs.txt"
```

### 4. Detectar Anomalías desde JSON
```bash
curl -X POST "http://localhost:8000/detect-text" \
     -H "Content-Type: application/json" \
     -d '[{"content": "2024-01-01 ERROR Failed to connect"}]'
```

## 📈 Ejemplo de Respuesta

```json
{
  "total_logs": 5,
  "anomalies_detected": 2,
  "anomalies": [
    {
      "log_entry": "2024-01-01 10:04:00 CRITICAL System memory usage exceeded 95%",
      "anomaly_score": -0.15,
      "is_anomaly": true,
      "explanation": "Este log es sospechoso porque indica un uso crítico de memoria del 95%, lo cual es una condición anómala que puede causar fallos del sistema."
    }
  ],
  "report_file": "report-20241109_094200.json"
}
```

## 🔧 Configuración

### Variables de Entorno
- `OLLAMA_SERVICE_URL`: URL del servicio Ollama
- `MODEL_NAME`: Nombre del modelo LLM (nidum-gemma-2b-uncensored-gguf)
- `OLLAMA_DEVICE`: Dispositivo para inferencia (nvidia)
- `PYTHONUNBUFFERED`: Para logs en tiempo real

### Archivo de Configuración
- **Ubicación:** `data/anomaly-detector/config/config.yml`
- **Contenido:** Parámetros de detección, LLM, palabras clave

## 📝 Próximos Pasos

1. **Optimización:** Ajustar parámetros de Isolation Forest
2. **Modelos:** Probar otros modelos LLM
3. **UI:** Crear interfaz web para visualización
4. **Alertas:** Implementar sistema de notificaciones
5. **Métricas:** Agregar monitoreo y métricas

## 🎯 Estado del Proyecto

✅ **Completado:**
- Estructura de directorios
- Dockerfile y docker-compose
- Servicio FastAPI completo
- Detección de anomalías con Isolation Forest
- Integración con LLM (Ollama/Gemma)
- Generación de reportes
- Scripts de prueba
- Documentación

🔄 **En Progreso:**
- Pruebas de integración
- Optimización de parámetros

📋 **Pendiente:**
- Interfaz web
- Sistema de alertas
- Monitoreo avanzado

---

**Fecha de implementación:** 9 de noviembre de 2024  
**Versión:** 1.0.0  
**Estado:** Funcional y listo para pruebas
