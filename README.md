# Detector de Anomalías en Logs

Sistema de detección de anomalías en logs utilizando Isolation Forest y LLM (Large Language Model) para análisis y explicación en lenguaje natural.

## Índice
1. [Descripción General](#descripción-general)
2. [Arquitectura](#arquitectura)
3. [Instalación Paso a Paso](#instalación-paso-a-paso)
4. [Configuración](#configuración)
5. [Uso del Sistema](#uso-del-sistema)
6. [Modelos LLM Soportados](#modelos-llm-soportados)
7. [Estructura de Directorios](#estructura-de-directorios)
8. [Flujos Principales](#flujos-principales)
9. [Características Clave](#características-clave)
   - [Fase de Evaluación Final](#-fase-de-evaluación-final-v21)
   - [UI de Procesos Activos](#-ui-de-procesos-activos)
   - [Prompts Optimizados](#-prompts-optimizados)
   - [Badges de Repetición](#-badges-de-repetición)
10. [Limitaciones y Consideraciones](#limitaciones-y-consideraciones)
11. [Solución de Problemas (FAQ)](#solución-de-problemas-faq)
12. [Roadmap](#roadmap-y-características-futuras)
13. [Historial de Versiones](#-historial-de-versiones)

## Descripción General

El detector de anomalías en logs es un sistema completo que combina algoritmos de machine learning (Isolation Forest) con modelos de lenguaje (LLM) para:

1. Procesar archivos de logs de gran tamaño
2. Detectar patrones anómalos o sospechosos
3. Proporcionar explicaciones en lenguaje natural sobre las anomalías detectadas
4. Visualizar resultados de manera intuitiva

### 🏆 Características Destacadas

- ✅ **Procesamiento de archivos grandes** (GB de logs) con chunks streaming
- ✅ **Sistema de Modelos LLM Configurable** (default, fallback, evaluadores por workspace)
- ✅ **Fase de Evaluación Final** (94-95% reducción en llamadas LLM)
- ✅ **Agrupamiento Inteligente** (90% similitud, formato con analogías)
- ✅ **Procesos Activos** UI (recuperación de estado al recargar la página)
- ✅ **Análisis en tiempo real** con streaming de resultados via SSE
- ✅ **Explicaciones mejoradas** por evaluadores especializados
- ✅ **Prompts optimizados** (sin lenguaje condescendiente, formato accesible)
- ✅ **Badges de repetición** (conteo de patrones similares en historial)
- ✅ **Clasificación de severidad** (critical, high, medium, low)
- ✅ **Gestión de proyectos** con workspaces y permisos RBAC
- ✅ **Prevención de duplicados** (agrupamiento y conteo de repeticiones)
- ✅ **Escalable** con Docker y microservicios

### 📊 Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|-----------|------------|--------|----------|
| Frontend | Vue 3 + Vite | 3.3.0 | Interfaz de usuario |
| UI Library | PrimeVue | 4.0.0 | Componentes UI |
| Backend | FastAPI + Uvicorn | 0.115.0 | API REST |
| ML Engine | Scikit-learn | 1.5.0 | Isolation Forest |
| LLM Service | Ollama Cloud | - | Modelos de lenguaje |
| Vector DB | Qdrant | latest | Embeddings semánticos |
| Databases | MongoDB + PostgreSQL + Redis | 7.0 / 15 / 7.2 | Almacenamiento |
| Proxy | Nginx | stable-alpine | Reverse proxy |
| Containerization | Docker + Compose | - | Orquestación |

## Arquitectura

El sistema está compuesto por los siguientes servicios en contenedores Docker:

```
┌─────────────────┐     ┌─────────────────────────────────────┐
│      Vue UI     │     │         FastAPI Server              │
│   (Frontend)    │────▶│      (Anomaly Detection)            │
│                 │     │  ┌───────────────────────────────┐  │
│ - Upload files  │     │  │ 1. Isolation Forest ML       │  │
│ - View results  │     │  │ 2. LLM Explanations          │  │
│ - ActiveJobs    │     │  │ 3. Final Evaluation Phase ✨  │  │
└─────────────────┘     │  └───────────────────────────────┘  │
        ▲                └─────────────────────────────────────┘
        │                             │
        │                             ▼
        │                      ┌─────────────────┐
        └──────────────────────│    Nginx        │
                               │  (Proxy Server)  │
                               └─────────────────┘
                                        │
                         ┌──────────────┼──────────────┐
                         ▼              ▼              ▼
                 ┌───────────┐  ┌─────────────┐  ┌─────────┐
                 │  MongoDB  │  │ PostgreSQL  │  │ Qdrant  │
                 │  (Logs)   │  │  (Auth/DB)  │  │(Vectors)│
                 └───────────┘  └─────────────┘  └─────────┘
                         │
                         ▼
                 ┌─────────────────┐
                 │  Ollama Cloud   │
                 │  (LLM Service)  │
                 │                 │
                 │ • Default Model │
                 │ • Fallback      │
                 │ • Evaluators ✨  │
                 └─────────────────┘
```

### Componentes

1. **Frontend (Vue3)**
   - Interfaz web para subida de archivos y visualización de resultados
   - Componentes PrimeVue para UI moderna
   - Estado global con Pinia
   - Historial de análisis persistente

2. **Backend (FastAPI)**
   - API REST para procesamiento de logs
   - Detección de anomalías usando Isolation Forest
   - Integración con Ollama Cloud para explicaciones
   - Streaming de resultados con Server-Sent Events
   - Autenticación JWT y RBAC

3. **LLM (Ollama Cloud)**
   - Servicio en la nube para modelos de lenguaje
   - Modelo configurable (por defecto: qwen2.5:3b)
   - Explicaciones en lenguaje natural
   - Procesamiento por lotes

4. **Nginx**
   - Proxy inverso
   - Serve de archivos estáticos
   - Configuración para streaming

5. **Bases de Datos**
   - MongoDB: Logs, chunks y resultados
   - PostgreSQL: Usuarios, workspaces, proyectos
   - Redis: Caché y pub/sub para streaming
   - Qdrant: Embeddings semánticos

## Estructura de Directorios

```
logsanomaly/
├── build/                      # Dockerfiles y configuraciones
│   ├── anomaly-detector/      # Servicio de detección
│   │   └── Dockerfile         # Imagen del backend
│   └── logs-analyze-ui/       # Frontend
│       └── Dockerfile         # Imagen del frontend
├── data/                       # Código de la aplicación
│   ├── backend-python/        # Backend (FastAPI)
│   │   ├── main.py            # API principal
│   │   ├── requirements.txt    # Dependencias Python
│   │   ├── config/            # Configuraciones
│   │   ├── models/            # Modelos de datos
│   │   │   ├── base/         # Clases base
│   │   │   ├── schemas/      # Pydantic schemas
│   │   │   ├── orm/          # SQLAlchemy ORM
│   │   │   └── factories/    # Conversiones ORM-API
│   │   ├── routes/            # Endpoints API
│   │   ├── services/          # Lógica de negocio
│   │   ├── middleware/        # Middleware de autenticación
│   │   └── debug/             # Scripts de prueba
│   ├── frontend/              # Frontend (Vue3)
│   │   ├── package.json       # Dependencias Node.js
│   │   ├── src/
│   │   │   ├── components/    # Componentes Vue
│   │   │   ├── stores/        # Estado global (Pinia)
│   │   │   ├── services/      # Servicios API
│   │   │   └── utils/         # Utilidades
│   │   └── dist/              # Archivos compilados
│   └── static/                # Archivos estáticos servidos por Nginx
├── doc/                       # Documentación
│   └── ...
├── server/                    # Configuraciones de servidor
│   └── nginx/                 # Configuración Nginx
│       └── conf.d/
├── docker-compose.yml          # Orquestación de servicios
├── env.template                # Template de variables de entorno
└── README.md                   # Este archivo
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

3. **Explicación LLM** (Procesamiento Inicial)
   ```python
   # Backend: Procesa anomalías en lotes durante el streaming
   async def process_anomalies_batch(anomalies):
       tasks = [get_llm_explanation(a) for a in anomalies]
       explanations = await asyncio.gather(*tasks)
       return combine_results(anomalies, explanations)
   ```

4. **Fase de Evaluación Final** (Nueva - v2.1)
   ```python
   # Backend: Se ejecuta al completar todos los chunks
   async def _run_final_evaluation(file_id: str):
       # 1. Agrupar anomalías similares (90% similitud)
       grouped = group_similar_logs(anomalies, threshold=0.90)

       # 2. Seleccionar ~10 representantes
       representatives = sample_representative_logs(grouped, max_samples=10)

       # 3. Evaluar con LLMs especializados
       improved = await evaluator_service.evaluate_explanation(representatives)

       # 4. Actualizar en MongoDB
       await update_anomalies_with_improved_explanations(improved)
   ```

### 3. Gestión de Estado

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

### 🆕 Fase de Evaluación Final (v2.1)

El sistema implementa una **fase de evaluación final** que optimiza drásticamente el uso de LLMs:

**¿Cómo funciona?**
1. Durante el procesamiento normal, se detectan todas las anomalías (ej: 100+)
2. Al finalizar el job, se agrupan anomalías similares (90% similitud)
3. Se seleccionan ~10 anomalías representativas (una por grupo)
4. Los evaluadores LLM mejoran solo estas representativas
5. Cada anomalía del grupo hereda la explicación mejorada

**Beneficios:**
- 🚀 **94-95% reducción** en llamadas LLM (de 100+ a ~10)
- 💰 **Ahorro significativo** en costos de API
- ⚡ **Procesamiento más rápido** sin sacrificar calidad
- 🎯 **Explicaciones consistentes** dentro de cada grupo

**Implementación:**
```python
# services/worker_service.py - _run_final_evaluation()
async def _run_final_evaluation(file_id: str):
    # 1. Obtener todas las anomalías
    results = await db_manager.mongodb_client.logsanomaly.results.find(
        {"chunk_id": {"$regex": f"^{file_id}"}}
    ).to_list(length=None)

    # 2. Agrupar por similitud (90%)
    grouped = group_similar_logs(anomalies, threshold=0.90, min_group_size=1)

    # 3. Seleccionar representantes (~10)
    representatives = sample_representative_logs(grouped, max_total_samples=10)

    # 4. Evaluar en lotes de 5
    for batch in chunked(representatives, 5):
        improved = await evaluator_service.evaluate_explanation(batch)
        # 5. Actualizar MongoDB
```

### 🆕 UI de Procesos Activos

Componente `ActiveJobsList.vue` que permite recuperar jobs al recargar:

**Características:**
- 📋 Lista de jobs en estado `processing` o `pending`
- 🔄 Auto-actualización cada 5 segundos
- 🔘 Botón "Ver progreso" para reconectar al stream
- 📊 Barra de progreso con estadísticas
- ⏱️ Tiempo transcurrido desde inicio
- Solo visible cuando hay jobs activos

**Endpoint:**
```
GET /jobs/active?project_id={uuid}
```

### 🆕 Prompts Optimizados

Los prompts ahora usan **lenguaje inclusivo y accesible**:

**Características:**
- ❌ **Sin prefacios condescendientes**: "Aquí tienes la explicación mejorada, enfocada en un público sin conocimientos técnicos:"
- ✅ **Explicaciones directas**: Empiezan con `• **Qué pasó**:` inmediatamente
- 🎨 **Formato con analogías**: Viñetas claras y comparaciones
- 🤝 **Lenguaje respetuoso**: "lenguaje claro y accesible" vs "sin conocimientos técnicos"

**Ejemplo de formato:**
```
• **Qué pasó**: El sistema intentó conectarse a la base de datos...
• **Por qué importa**: Sin conexión, las aplicaciones no funcionan...
• **Qué hacer**: Verificar que el servicio de base de datos esté activo...
```

### 🆕 Badges de Repetición

Las anomalías agrupadas muestran cuántas veces se repiten:

```vue
<Tag v-if="anomaly.group_size && anomaly.group_size > 1"
     :value="`Se repite ${anomaly.group_size} veces`"
     severity="info" />
```

**Endpoint `/reports` mejorado:**
- Agrupamiento con 90% similitud (antes 95%)
- `min_group_size: 1` para agrupar TODO
- Priorización de anomalías con mejor explicación
- Ordenamiento por frecuencia

### 1. Procesamiento de Archivos Grandes
- División en chunks de 500KB
- Procesamiento incremental
- Streaming de resultados
- Progreso en tiempo real
- Detección de duplicados por hash SHA-256

### 2. Detección de Anomalías
- Uso de Isolation Forest
- Features: longitud, entropía, palabras clave
- Scoring y clasificación
- Procesamiento paralelo
- Búsqueda semántica con embeddings

### 3. Explicaciones IA
- Integración con Ollama Cloud
- Modelos configurables (Qwen 2.5, Llama 3, etc.)
- Procesamiento por lotes
- Respuestas estructuradas

### 4. Visualización de Resultados
- Vista de detalle de anomalías con acordeón
- Clasificación por severidad (Crítica, Alta, Media, Baja)
- Barra de progreso con score de anomalía
- Paginación para grandes volúmenes
- Log original formateado

### 5. Gestión de Análisis
- Re-análisis de archivos existentes
- Eliminación de análisis completos
- Historial persistente
- Agrupación por proyectos

### 6. Control de Acceso (RBAC)
- Workspaces para separar entornos
- Proyectos por workspace
- Roles y permisos configurables
- Autenticación JWT

## Ejemplos de Uso y Resultados

### Ejemplo de Log Normal
```
2024-01-15 10:30:15 INFO [UserService] User login successful: user123@example.com
2024-01-15 10:30:16 INFO [OrderService] Order created: ID=12345, User=user123
2024-01-15 10:30:17 INFO [PaymentService] Payment processed: $25.99
```
**Resultado**: Sin anomalías detectadas

### Ejemplo de Log Anómalo
```
2024-01-15 10:30:15 ERROR [AuthService] Multiple failed login attempts from 192.168.1.100
2024-01-15 10:30:16 ERROR [AuthService] SQL injection attempt detected: admin' OR '1'='1
2024-01-15 10:30:17 CRITICAL [SecurityService] Unauthorized access attempt to /admin/users
```
**Resultado**: ⚠️ **Anomalía detectada**
- **Score**: -0.85
- **Severidad**: Alta
- **Explicación**: "Se detecta un posible ataque de fuerza bruta seguido de intento de inyección SQL y acceso no autorizado. Se recomienda bloquear la IP 192.168.1.100."

### Visualización en la Interfaz

Al hacer clic en una anomalía, se muestra:

```
┌─────────────────────────────────────────────────────────┐
│ 🔴 Anomalía #1                    [ALTA]                │
├─────────────────────────────────────────────────────────┤
│ Log detectado:                                          │
│ 2024-01-15 10:30:15 ERROR [AuthService] Multiple        │
│ failed login attempts from 192.168.1.100                │
│                                                         │
│ Explicación:                                            │
│ Se detecta un posible ataque de fuerza bruta...         │
│                                                         │
│ Score de anomalía: ███████████████████░░░░ 85%          │
└─────────────────────────────────────────────────────────┘
```

### Demo en Vivo

Puede probar el sistema con archivos de ejemplo:
1. `logs/ejemplo_normal.log` - Logs típicos de aplicación
2. `logs/ejemplo_anomalias.log` - Logs con patrones sospechosos
3. `logs/ejemplo_mixto.log` - Combinación de logs normales y anómalos

## Instalación Paso a Paso

> 🚀 **¿Tienes prisa?** Ve a la [Guía de Instalación Rápida](./INSTALACION-RAPIDA.md) para tenerlo funcionando en 5 minutos.

### 1. Requisitos Previos

- **Sistema Operativo**: Windows, macOS o Linux
- **Docker**: v20.10 o superior
- **Docker Compose**: v2.0 o superior
- **Hardware Recomendado**:
  - CPU: 4 cores o más
  - RAM: 8GB mínimo (16GB recomendado para mejores resultados)
  - Almacenamiento: 10GB libres mínimo
  - Conexión a internet (requerido para Ollama Cloud)

### 2. Instalación Básica

```bash
# Clonar el repositorio
git clone https://github.com/ctangarife/reto-ia-log-analyzer.git
cd reto-ia-log-analyzer

# Copiar template de variables de entorno
cp env.template .env

# Editar .env y agregar la API key de Ollama Cloud
# OLLAMA_API_KEY=tu_api_key_aqui

# Levantar los servicios
docker-compose up -d
```

### 3. Verificación de Instalación

Una vez iniciados los servicios, puede verificar que todo esté funcionando correctamente:

```bash
# Ver estado de los contenedores
docker-compose ps

# Ver logs de los servicios
docker-compose logs -f
```

Acceda a la interfaz web a través de http://localhost:80

## Configuración

### Configuración del LLM (Modelo de Lenguaje)

El sistema utiliza **Ollama Cloud** para generar explicaciones en lenguaje natural. Por defecto usa el modelo `qwen2.5:3b`, pero puede configurar cualquier modelo disponible en Ollama.

#### Variables de Entorno

Edite el archivo `.env` para configurar el servicio LLM:

```bash
# Ollama Cloud Configuration
OLLAMA_API_KEY=tu_api_key_aqui
OLLAMA_URL=https://ollama.com
OLLAMA_MODEL=qwen2.5:3b  # Modelo a utilizar
```

#### Modelos Recomendados

- `qwen2.5:3b` - Ligero y rápido (recomendado)
- `llama3:8b` - Mayor calidad pero más lento
- `gemma:7b` - Buen balance calidad/rendimiento
- `phi3:mini` - Modelo muy ligero para recursos limitados

### Configuración del Sistema

#### Parámetros de Detección

Para ajustar la sensibilidad del detector de anomalías, edite el archivo `data/backend-python/main.py`:

```python
isolation_forest = IsolationForest(
    contamination=0.1,  # Porcentaje de anomalías esperado (0.1 = 10%)
    random_state=42,
    n_estimators=100  # Más estimadores = mayor precisión pero más lento
)
```

## Uso del Sistema

### 1. Acceso a la Interfaz

Abra su navegador y vaya a http://localhost:80

### 2. Análisis de Logs

1. **Seleccionar Proyecto**: Elija el workspace y proyecto donde desea trabajar
2. **Subir Archivo**: Arrastre y suelte su archivo de logs o haga clic en el área de carga
3. **Iniciar Análisis**: Haga clic en el botón "Analizar"
4. **Ver Progreso**: El progreso se muestra en tiempo real con porcentaje y estadísticas
5. **Resultados**: Al completarse, verá el resumen con total de logs y anomalías detectadas

### 3. Visualización de Detalles

Para ver el detalle de las anomalías detectadas:

1. Vaya a la sección "Historia"
2. Haga clic en el icono de ojo (👁) del análisis que desea revisar
3. Se mostrará:
   - **Resumen**: Total de logs, anomalías y porcentaje
   - **Detalle de anomalías**: Lista expandible con cada anomalía
   - **Información de cada anomalía**:
     - Log original formateado
     - Explicación en lenguaje natural
     - Score de anomalía (barra de progreso)
     - Nivel de severidad (Crítica, Alta, Media, Baja)

### 4. Gestión de Análisis

En el historial puede realizar las siguientes acciones:

- **Ver detalles** (👁): Muestra el contenido completo de las anomalías
- **Re-analizar** (🔄): Crea un nuevo análisis del mismo archivo
- **Eliminar** (🗑): Elimina el análisis y todos sus datos

### 5. Organización por Workspaces y Proyectos

- **Workspaces**: Entornos separados (ej: Desarrollo, Producción)
- **Proyectos**: Agrupaciones de análisis dentro de un workspace
- **Permisos**: Control de acceso basado en roles (Viewer, Analyst, Admin)

## Modelos LLM Soportados

El sistema utiliza Ollama Cloud para generar explicaciones. El modelo se puede cambiar mediante la variable de entorno `OLLAMA_MODEL`.

### Modelos Disponibles

- `qwen2.5:3b` - Ligero y rápido (por defecto)
- `llama3:8b` - Mayor calidad
- `gemma:7b` - Buen balance
- `phi3:mini` - Muy ligero

### Cambiar de Modelo

Edite el archivo `.env`:
```bash
OLLAMA_MODEL=llama3:8b
```

Luego reinicie el backend:
```bash
docker-compose restart anomaly-detector
```

## Limitaciones y Consideraciones

1. **Rendimiento**
   - El tamaño de chunk afecta memoria y velocidad
   - Ollama Cloud puede tener latencia de red
   - Considerar batch size vs tiempo de respuesta
   - El número de anomalías afecta el tiempo de explicación

2. **Almacenamiento**
   - Chunks y resultados ocupan espacio en MongoDB
   - Los embeddings en Qdrant consumen memoria
   - Implementar limpieza periódica de análisis antiguos
   - Monitorear uso de disco

3. **Escalabilidad**
   - Vertical: Aumentar recursos (RAM y CPU)
   - Horizontal: Múltiples workers de procesamiento
   - Considerar modelos más pequeños para mayor eficiencia
   - Rate limiting de Ollama Cloud según plan contratado

## Solución de Problemas (FAQ)

### Problemas Comunes de Instalación

#### Error: "No se puede conectar a Docker"
**Solución**:
1. Verificar que Docker Desktop esté ejecutándose
2. Verificar permisos: `docker run hello-world`
3. Reiniciar Docker Desktop si es necesario

#### Error: "Out of memory" durante la descarga del modelo
**Solución**:
```yaml
# En docker-compose.yml, reducir límites de memoria:
deploy:
  resources:
    limits:
      memory: 8G  # Reducir de 16G a 8G
```
O usar un modelo más ligero como `phi3:mini`

### Problemas de Rendimiento

#### El análisis de logs es muy lento
**Soluciones**:
1. **Reducir tamaño de chunk** en el backend
2. **Verificar conexión a internet** para Ollama Cloud
3. **Considerar plan superior** de Ollama Cloud para mayor rate limit

3. **Ajustar tamaño de chunk** en el backend

#### La descarga del modelo toma demasiado tiempo
**Opciones**:
1. Usar un modelo predesacargado
2. Cambiar a un modelo más pequeño temporalmente
3. Verificar conexión a internet

### Problemas de Configuración

#### ¿Cómo obtener una API key de Ollama Cloud?
1. Visite https://ollama.com
2. Regístrese o inicie sesión
3. Genere una API key en la sección de configuración
4. Agréguela al archivo `.env` como `OLLAMA_API_KEY`

#### ¿Cómo cambiar la base de datos?
Por defecto usa MongoDB, PostgreSQL, Redis y Qdrant. Para configurar conexiones personalizadas, edite el archivo `.env`:
```bash
# MongoDB
MONGODB_URI=mongodb://admin:password@mongodb:27017/logsanomaly?authSource=admin

# PostgreSQL
POSTGRES_USER=anomaly_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=logsanomaly

# Redis
REDIS_URL=redis://redis:6379

# Qdrant
QDRANT_URL=http://qdrant:6333
```

#### ¿Cómo ajustar la sensibilidad de detección?
Edite `data/backend-python/main.py`:
```python
# Valores más bajos = más sensible (más anomalías detectadas)
isolation_forest = IsolationForest(
    contamination=0.05,  # Cambiar de 0.1 a 0.05 para más sensibilidad
    random_state=42,
    n_estimators=100
)
```

### Comandos Útiles

#### Monitoreo del Sistema
```bash
# Ver uso de recursos
docker stats

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f logs-analyze-detector
```

#### Limpieza y Mantenimiento
```bash
# Limpiar archivos temporales
docker-compose down
docker system prune -f

# Limpiar volúmenes (¡CUIDADO: Elimina todos los datos!)
docker-compose down -v

# Reconstruir imágenes
docker-compose build --no-cache
```

#### Backup y Restauración
```bash
# Backup de los datos
docker run --rm -v logsanomaly_mongodb_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mongodb-backup.tar.gz -C /data .

# Backup de PostgreSQL
docker exec logs-analyze-postgres pg_dump -U anomaly_user logsanomaly > backup.sql
```

### Contacto y Soporte

- **Repositorio**: [GitHub](https://github.com/ctangarife/reto-ia-log-analyzer)
- **Issues**: Para reportar bugs o solicitar características en [GitHub Issues](https://github.com/ctangarife/reto-ia-log-analyzer/issues)
- **Documentación**: Wiki del repositorio para información adicional

### Contribuir al Proyecto

1. Fork del repositorio
2. Crear rama para nueva característica: `git checkout -b feature/nueva-caracteristica`
3. Commit de cambios: `git commit -am 'Add nueva-caracteristica'`
4. Push a la rama: `git push origin feature/nueva-caracteristica`
5. Crear Pull Request

## Licencia

Este proyecto está licenciado bajo la Licencia MIT. Consulte el archivo [LICENSE](LICENSE) para más detalles.

## Roadmap y Características Futuras

### 🗺️ Próximas Características

#### En Desarrollo
- [ ] **Paginador en vista de análisis**: Para grandes volúmenes de anomalías
- [ ] **Loader para fase de evaluación**: Mostrar progreso de evaluadores LLM
- [ ] **Propagación de explicaciones**: Actualizar todas las anomalías del grupo con la mejorada
- [ ] **Sistema de modelos LLM**: Integración completa de default/fallback/evaluators

#### Planeado
- [ ] **API de integración**: Endpoints para sistemas externos
- [ ] **Alertas en tiempo real**: Notificaciones por email/Slack
- [ ] **Dashboard avanzado**: Métricas y gráficos detallados
- [ ] **Exportación avanzada**: PDF, Excel, reportes programados
- [ ] **Integración con SIEM**: Conectores para sistemas de seguridad
- [ ] **Análisis predictivo**: Predicción de anomalías futuras
- [ ] **Correlación de eventos**: Análisis multi-fuente

### 🗓️ Historial de Versiones

#### v2.1.0 (2026-04-21) - Evaluación Final y UX Mejorada
- ✨ **Fase de Evaluación Final**: 94-95% reducción en llamadas LLM
- 🎨 **Prompts optimizados**: Eliminado lenguaje condescendiente
- 🔄 **UI de Procesos Activos**: Recuperación de estado al recargar página
- 🏷️ **Badges de repetición**: Conteo de patrones similares
- 📊 **Mejoras en agrupamiento**: 90% similitud, priorización inteligente
- 🔧 **Sistema de selección de modelos**: Default, fallback, evaluadores por workspace
- 🐛 **Correcciones**: Import faltantes, métodos renombrados

#### v2.0.0
- Visualización de detalles de anomalías con acordeón
- Clasificación por severidad (Crítica, Alta, Media, Baja)
- Paginación para grandes volúmenes de anomalías
- Re-análisis de archivos existentes
- Eliminación de análisis completos
- Detección de duplicados por hash SHA-256
- Control de acceso RBAC con workspaces y proyectos
- Integración con Ollama Cloud
- Búsqueda semántica con Qdrant

#### v1.0.0
- Detección de anomalías con Isolation Forest
- Explicaciones con modelos LLM
- Interfaz web con Vue 3
- Soporte para archivos grandes
- Múltiples bases de datos integradas

## Mejores Prácticas de Uso

### Para Análisis de Seguridad
1. **Organizar por proyectos**: Cree workspaces y proyectos separados por entorno
2. **Revisar severidades**: Priorice anomalías con nivel "Crítico" y "Alto"
3. **Usar re-análisis**: Para comparar cambios en el comportamiento
4. **Mantener historial**: No elimine análisis antiguos para comparación temporal

### Para Optimización de Rendimiento
1. **Limpiar datos antiguos**: Elimine análisis que ya no necesite
2. **Ajustar parámetros**: Configure contaminación según sus necesidades
3. **Monitorear recursos**: Verificar uso de CPU, RAM y almacenamiento
4. **Usar paginación**: Para grandes volúmenes de anomalías

### Para Gestión de Equipos
1. **Asignar roles**: Use roles apropiados (Viewer, Analyst, Admin)
2. **Separar entornos**: Use workspaces para Desarrollo/Producción
3. **Documentar proyectos**: Asigne nombres descriptivos a los proyectos
4. **Revisar permisos**: Audite regularmente el acceso a los proyectos

## Agradecimientos

- **Ollama Cloud** por proporcionar una plataforma excelente para modelos LLM
- **FastAPI** por el framework web rápido y robusto
- **Vue.js** por el framework frontend intuitivo
- **PrimeVue** por los componentes UI de alta calidad
- **Scikit-learn** por los algoritmos de machine learning
- **Qdrant** por la base de datos de vectores
- Comunidad de código abierto por las bibliotecas y herramientas

---

**📝 Nota**: Este README se actualiza regularmente. Para la información más reciente, consulte la [documentación completa](https://github.com/ctangarife/reto-ia-log-analyzer/wiki) o los [issues del proyecto](https://github.com/ctangarife/reto-ia-log-analyzer/issues).
