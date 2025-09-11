# Detector de Anomalías en Logs

Sistema de detección de anomalías en logs utilizando Isolation Forest y LLM (Large Language Model) para análisis y explicación en lenguaje natural.

## Arquitectura

El sistema está compuesto por tres servicios principales que se ejecutan en contenedores Docker:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      Vue UI     │     │  FastAPI Server │     │  Ollama Service │
│   (Frontend)    │────▶│(Anomaly Detect) │────▶│    (LLM)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       │
        │                       ▼
        │               ┌─────────────────┐
        └───────────── │    Nginx        │
                      │  (Proxy Server)  │
                      └─────────────────┘
```

### Componentes

1. **Frontend (Vue3)**
   - Interfaz web para subida de archivos y visualización de resultados
   - Manejo de archivos grandes mediante chunking
   - Visualización en tiempo real del procesamiento
   - Historial de análisis persistente

2. **Backend (FastAPI)**
   - API REST para procesamiento de logs
   - Detección de anomalías usando Isolation Forest
   - Integración con Ollama para explicaciones en lenguaje natural
   - Procesamiento por chunks y streaming de resultados

3. **LLM (Ollama)**
   - Servicio local de LLM usando Nidum-Gemma-2B-Uncensored
   - Generación de explicaciones en lenguaje natural
   - Procesamiento por lotes para optimización

4. **Nginx**
   - Proxy inverso
   - Manejo de archivos grandes
   - Configuración para streaming

## Estructura de Directorios

```
logsanomaly/
├── build/                      # Dockerfiles
│   ├── anomaly-detector/      # Servicio de detección
│   ├── ollama/               # Servicio LLM
│   └── nginx/                # Configuración proxy
├── data/
│   ├── anomaly-detector/     # Código del backend
│   │   ├── main.py          # API principal
│   │   ├── config/          # Configuraciones
│   │   ├── scripts/         # Scripts auxiliares
│   │   ├── chunks/          # Almacenamiento temporal
│   │   └── reports/         # Reportes generados
│   └── ui/                  # Frontend Vue3
│       ├── src/
│       │   ├── components/  # Componentes Vue
│       │   ├── stores/      # Estado global (Pinia)
│       │   └── utils/       # Utilidades
└── docker-compose.yml       # Orquestación de servicios
```

## Flujos Principales

### 1. Procesamiento de Logs

1. **Subida y Chunking**
   ```javascript
   // Frontend: Divide archivo en chunks manejables
   const chunks = await splitLogFile(file)  // 500KB por chunk
   for (const chunk of chunks) {
     const formData = new FormData()
     formData.append('file', createChunkFile(chunk))
     // Envío y procesamiento streaming...
   }
   ```

2. **Detección de Anomalías**
   ```python
   # Backend: Procesa cada chunk
   def detect_anomalies(log_lines):
       features = extract_features(log_lines)
       scores = isolation_forest.predict(features)
       return process_anomalies(log_lines, scores)
   ```

3. **Explicación LLM**
   ```python
   # Backend: Procesa anomalías en lotes
   async def process_anomalies_batch(anomalies):
       tasks = [get_llm_explanation(a) for a in anomalies]
       explanations = await asyncio.gather(*tasks)
       return combine_results(anomalies, explanations)
   ```

### 2. Gestión de Estado

1. **Store Global (Pinia)**
   ```typescript
   // Frontend: Manejo de estado
   const analysisStore = defineStore('analysis', {
     state: () => ({
       analysisHistory: [],
       currentAnalysis: null
     }),
     actions: {
       addAnalysis(result) {
         // Actualización de histórico...
       }
     }
   })
   ```

2. **Persistencia de Resultados**
   ```python
   # Backend: Guarda resultados por archivo
   def save_report(file_id, results):
       report_path = f"/app/chunks/{file_id}/report_{timestamp}.json"
       with open(report_path, 'w') as f:
           json.dump(results, f)
   ```

## Características Clave

1. **Procesamiento de Archivos Grandes**
   - División en chunks de 500KB
   - Procesamiento incremental
   - Streaming de resultados
   - Progreso en tiempo real

2. **Detección de Anomalías**
   - Uso de Isolation Forest
   - Features: longitud, entropía, palabras clave
   - Scoring y clasificación
   - Procesamiento paralelo

3. **Explicaciones IA**
   - Modelo local Nidum-Gemma-2B
   - Procesamiento por lotes
   - Prompts optimizados
   - Respuestas estructuradas

4. **UI/UX**
   - Carga de archivos con drag & drop
   - Visualización en tiempo real
   - Historial persistente
   - Agrupación por archivos

## Configuración y Despliegue

1. **Requisitos**
   - Docker y Docker Compose
   - GPU (opcional, mejora rendimiento LLM)
   - 16GB RAM mínimo recomendado

2. **Instalación**
   ```bash
   # Clonar repositorio
   git clone [repo-url]
   cd logsanomaly

   # Iniciar servicios
   docker-compose up -d
   ```

3. **Configuración**
   - Ajustar límites de memoria en `docker-compose.yml`
   - Configurar tamaño de chunks en frontend
   - Modificar parámetros de Isolation Forest
   - Ajustar timeouts de Nginx

## Limitaciones y Consideraciones

1. **Rendimiento**
   - Tamaño de chunk afecta memoria y velocidad
   - LLM puede ser cuello de botella
   - Considerar batch size vs latencia

2. **Almacenamiento**
   - Chunks y reportes ocupan espacio
   - Implementar limpieza periódica
   - Monitorear uso de disco

3. **Escalabilidad**
   - Vertical: Aumentar recursos
   - Horizontal: Múltiples workers
   - Caché de LLM para respuestas comunes