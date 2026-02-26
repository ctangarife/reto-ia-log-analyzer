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
10. [Limitaciones y Consideraciones](#limitaciones-y-consideraciones)
11. [Solución de Problemas (FAQ)](#solución-de-problemas-faq)

## Descripción General

El detector de anomalías en logs es un sistema completo que combina algoritmos de machine learning (Isolation Forest) con modelos de lenguaje (LLM) para:

1. Procesar archivos de logs de gran tamaño
2. Detectar patrones anómalos o sospechosos
3. Proporcionar explicaciones en lenguaje natural sobre las anomalías detectadas
4. Visualizar resultados de manera intuitiva

### 🏆 Características Destacadas

- ✅ **Procesamiento de archivos grandes** (GB de logs)
- ✅ **Modelo de IA configurable** (cualquier modelo de Ollama)
- ✅ **Interfaz web intuitiva** con drag & drop
- ✅ **Análisis en tiempo real** con streaming de resultados
- ✅ **Explicaciones en lenguaje natural** de las anomalías
- ✅ **Historial persistente** de análisis
- ✅ **Escalable** con Docker y microservicios
- ✅ **Soporte GPU/CPU** para mejor rendimiento

### 📊 Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|-----------|------------|--------|----------|
| Frontend | Vue 3 + Vite | 3.3.0 | Interfaz de usuario |
| UI Library | PrimeVue | 3.40.0 | Componentes UI |
| Backend | FastAPI + Uvicorn | 0.104.1 | API REST |
| ML Engine | Scikit-learn | 1.3.2 | Isolation Forest |
| LLM Service | Ollama | 0.5.8 | Modelos de lenguaje |
| Databases | MongoDB + PostgreSQL + Redis | 7.0 / 15 / 7.2 | Almacenamiento |
| Proxy | Nginx | stable-alpine | Reverse proxy |
| Containerization | Docker + Compose | - | Orquestación |

## Arquitectura

El sistema está compuesto por los siguientes servicios en contenedores Docker:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      Vue UI     │     │  FastAPI Server │     │  Ollama Service │
│   (Frontend)    │────▶│(Anomaly Detect) │────▶│    (LLM)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       │                        │
        │                       ▼                        │
        │               ┌─────────────────┐              │
        └───────────── │    Nginx        │              ▼
                      │  (Proxy Server)  │     ┌─────────────────┐
                      └─────────────────┘     │  Base de Datos   │
                                             │  (MongoDB, etc.) │
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
   - Servicio local de LLM (modelo configurable)
   - Por defecto usa Qwen 2.5 3B, pero se puede usar cualquier modelo compatible con Ollama
   - Generación de explicaciones en lenguaje natural
   - Procesamiento por lotes para optimización

4. **Nginx**
   - Proxy inverso
   - Manejo de archivos grandes
   - Configuración para streaming

5. **Bases de Datos**
   - MongoDB: Almacenamiento de logs y reportes
   - PostgreSQL: Gestión de usuarios y configuraciones
   - Redis: Caché y gestión de colas de procesamiento

## Estructura de Directorios

```
logsanomaly/
├── build/                      # Dockerfiles y configuraciones
│   ├── anomaly-detector/      # Servicio de detección
│   │   └── Dockerfile         # Imagen del backend
│   ├── ollama/               # Servicio LLM
│   │   ├── Dockerfile         # Imagen de Ollama
│   │   └── init-ollama.sh     # Script de inicialización
│   ├── ui/                   # Frontend
│   │   └── Dockerfile         # Imagen del frontend
│   ├── mongodb/              # Configuración MongoDB
│   │   └── init-mongo.js      # Script de inicialización
│   └── redis/                # Configuración Redis
│       └── redis.conf         # Archivo de configuración
├── data/                       # Código de la aplicación
│   ├── backend-python/        # Backend (FastAPI)
│   │   ├── main.py            # API principal
│   │   ├── requirements.txt    # Dependencias Python
│   │   ├── config/            # Configuraciones
│   │   ├── scripts/           # Scripts auxiliares
│   │   ├── chunks/            # Almacenamiento temporal
│   │   └── reports/           # Reportes generados
│   ├── frontend/              # Frontend (Vue3)
│   │   ├── package.json       # Dependencias Node.js
│   │   ├── src/
│   │   │   ├── components/    # Componentes Vue
│   │   │   ├── stores/        # Estado global (Pinia)
│   │   │   └── utils/         # Utilidades
│   │   └── dist/              # Archivos compilados
│   ├── models/                # Modelos LLM descargados
│   │   └── ollama/            # Modelos de Ollama
│   └── static/                # Archivos estáticos servidos por Nginx
├── db/                        # Scripts de bases de datos
│   ├── init.sql              # Inicialización PostgreSQL
│   └── init-mongo.js         # Inicialización MongoDB
├── doc/                       # Documentación
│   ├── Arquitectura.MD
│   ├── CONTEXT.md
│   ├── FEATURES.md
│   └── ...
├── server/                    # Configuraciones de servidor
│   └── nginx/                 # Configuración Nginx
│       ├── nginx.conf
│       ├── conf.d/
│       └── includes/
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
**Resultado**: ⚠️ **Anomalía detectada** - Score: -0.85  
**Explicación IA**: "Se detecta un posible ataque de fuerza bruta seguido de intento de inyección SQL y acceso no autorizado. Recomiendo bloquear la IP 192.168.1.100 y revisar los logs de seguridad."

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
  - RAM: 16GB mínimo (32GB recomendado para mejores resultados)
  - Almacenamiento: 10GB libres mínimo
  - GPU: NVIDIA compatible con CUDA (opcional, mejora significativamente el rendimiento del LLM)

### 2. Instalación Básica

```bash
# Clonar el repositorio
git clone https://github.com/ctangarife/reto-ia-log-analyzer.git
cd reto-ia-log-analyzer

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

**El modelo de lenguaje es totalmente configurable y opcional**. Por defecto, el sistema usa `qwen2.5:3b`, pero puede configurar cualquier modelo compatible con Ollama.

Para cambiar el modelo, edite las siguientes líneas en el archivo `docker-compose.yml`:

```yaml
# En el servicio anomaly-detector (usar archivo .env)
# OLLAMA_SERVICE_URL=http://ollama-service:11434
# MODEL_NAME=qwen2.5:3b  # Cambie a su modelo preferido

# En el servicio ollama-service
environment:
  - OLLAMA_HOST=0.0.0.0
  - OLLAMA_DEVICE=nvidia
  - OLLAMA_MODEL=qwen2.5:3b  # Cambie a su modelo preferido
```

Modelos recomendados:
- `llama3:8b` - Mayor calidad pero requiere más recursos
- `gemma:7b` - Buen balance calidad/rendimiento
- `phi3:mini` - Modelo ligero para equipos con recursos limitados
- Cualquier modelo compatible con Ollama

### Configuración del Sistema

#### Ajustes de Hardware

Ajuste los límites de recursos en `docker-compose.yml` según las capacidades de su sistema:

```yaml
# Para el servicio de Ollama (LLM)
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [ gpu ]
    limits:
      memory: 16G  # Ajuste según la RAM disponible
```

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

1. **Subir Archivo**: Arrastre y suelte su archivo de logs o haga clic en el área de carga
2. **Configuración de Análisis**: Establezca los parámetros según necesite
3. **Iniciar Análisis**: Haga clic en el botón "Analizar"
4. **Ver Resultados**: Los resultados se mostrarán en tiempo real a medida que se procesan

### 3. Gestión de Reportes

- Los reportes se guardan automáticamente y están disponibles en la sección "Historial"
- Cada reporte incluye estadísticas generales y detalles de las anomalías detectadas
- Puede exportar los resultados en formato JSON o CSV

## Modelos LLM Soportados

El sistema es compatible con cualquier modelo disponible en Ollama. La elección del modelo dependerá del hardware disponible y la calidad deseada de las explicaciones.

### ¿Cómo cambiar el modelo?

1. **Opción 1**: Cambiar la variable de entorno en docker-compose.yml (como se explicó anteriormente)

2. **Opción 2**: Usar un modelo ya descargado
   ```bash
   # Primero descargar el modelo deseado
   docker exec logs-analyze-ollama ollama pull llama3:8b
   
   # Luego editar docker-compose.yml y reiniciar los servicios
   docker-compose down
   docker-compose up -d
   ```

3. **Opción 3**: Crear un modelo personalizado
   ```bash
   # Conectarse al contenedor de Ollama
   docker exec -it logs-analyze-ollama bash
   
   # Crear un modelo personalizado
   cat > /tmp/Modelfile << EOF
   FROM llama3:8b
   PARAMETER temperature 0.7
   PARAMETER stop "User:"
   PARAMETER stop "Assistant:"
   EOF
   
   # Registrar el modelo
   ollama create mi-modelo-personalizado -f /tmp/Modelfile
   
   # Salir del contenedor
   exit
   ```
   Luego actualice las variables de entorno en docker-compose.yml con `MODEL_NAME=mi-modelo-personalizado`

### Configuración Avanzada de Modelos

Para configuraciones más detalladas, ejemplos específicos por hardware y scripts de automatización, consulte el documento [CONFIGURACION-MODELOS.md](./CONFIGURACION-MODELOS.md).

## Limitaciones y Consideraciones

1. **Rendimiento**
   - Tamaño de chunk afecta memoria y velocidad
   - LLM puede ser cuello de botella (especialmente sin GPU)
   - Considerar batch size vs latencia
   - Tiempo de descarga inicial del modelo puede ser significativo

2. **Almacenamiento**
   - Chunks y reportes ocupan espacio
   - Modelos LLM pueden requerir varios GB de almacenamiento
   - Implementar limpieza periódica
   - Monitorear uso de disco

3. **Escalabilidad**
   - Vertical: Aumentar recursos (especialmente RAM para modelos grandes)
   - Horizontal: Múltiples workers
   - Caché de LLM para respuestas comunes
   - Considerar modelos más pequeños para mayor eficiencia

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
O usar un modelo más pequeño como `phi3:mini`

#### El servicio Ollama no responde
**Solución**:
```bash
# Verificar estado del contenedor
docker logs logs-analyze-ollama

# Si necesita reiniciar solo el servicio Ollama
docker-compose restart ollama-service
```

### Problemas de Rendimiento

#### El análisis de logs es muy lento
**Soluciones**:
1. **Sin GPU**: Usar modelos más pequeños
   ```yaml
   environment:
     - MODEL_NAME=phi3:mini  # Modelo ligero
   ```

2. **Con GPU**: Verificar que NVIDIA Docker esté instalado
   ```bash
   # Verificar GPU disponible
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

3. **Ajustar tamaño de chunk** en el backend

#### La descarga del modelo toma demasiado tiempo
**Opciones**:
1. Usar un modelo predesacargado
2. Cambiar a un modelo más pequeño temporalmente
3. Verificar conexión a internet

### Problemas de Configuración

#### ¿Cómo usar el sistema sin GPU?
**Configuración**:
```yaml
# Comentar o eliminar la sección de GPU en docker-compose.yml
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: all
#           capabilities: [ gpu ]

# Cambiar variables de entorno
environment:
  - OLLAMA_DEVICE=cpu
  - MODEL_NAME=phi3:mini  # Usar modelo ligero
```

#### ¿Cómo cambiar la base de datos?
Por defecto usa MongoDB, PostgreSQL y Redis. Para usar solo una:
```yaml
# En docker-compose.yml, comentar los servicios no deseados
# y ajustar las variables de entorno en el archivo .env
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

# Ver modelos descargados
docker exec logs-analyze-ollama ollama list
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

# Backup de los modelos
docker run --rm -v logs-analyze-ollama_models:/models -v $(pwd):/backup ubuntu tar czf /backup/models-backup.tar.gz -C /models .
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

- [ ] **API de integración**: Endpoints para sistemas externos
- [ ] **Alertas en tiempo real**: Notificaciones por email/Slack
- [ ] **Dashboard avanzado**: Métricas y gráficos detallados
- [ ] **Modelos personalizados**: Entrenamiento con datos específicos
- [ ] **Soporte multi-tenant**: Separación por organizaciones
- [ ] **Exportación avanzada**: PDF, Excel, reportes programados
- [ ] **Integración con SIEM**: Conectores para sistemas de seguridad
- [ ] **Análisis predictivo**: Predicción de anomalías futuras

### 🗓️ Historial de Versiones

- **v1.0.0** (Actual)
  - Detección de anomalías con Isolation Forest
  - Explicaciones con modelos LLM configurables
  - Interfaz web completa con Vue 3
  - Soporte para archivos grandes
  - Múltiples bases de datos integradas

## Mejores Prácticas de Uso

### Para Análisis de Seguridad
1. **Configurar alertas**: Establecer umbrales para anomalías críticas
2. **Revisar regularmente**: Programar análisis automáticos
3. **Correlacionar eventos**: Analizar patrones en ventanas de tiempo
4. **Mantener contexto**: Incluir logs de múltiples fuentes

### Para Optimización de Rendimiento
1. **Ajustar chunk size**: Balancear memoria vs velocidad
2. **Usar GPU cuando esté disponible**: Significativa mejora en LLM
3. **Limpiar regularmente**: Eliminar archivos temporales antiguos
4. **Monitorear recursos**: Verificar uso de CPU, RAM y almacenamiento

### Para Desarrollo y Testing
1. **Usar modelos ligeros**: `phi3:mini` para desarrollo rápido
2. **Configurar logs detallados**: Para debugging efectivo
3. **Probar con datos reales**: Validar con logs de producción
4. **Documentar configuraciones**: Mantener registro de parámetros

## Agradecimientos

- **Ollama** por proporcionar una excelente plataforma para modelos LLM locales
- **FastAPI** por el framework web rápido y robusto
- **Vue.js** por el framework frontend intuitivo
- **Scikit-learn** por los algoritmos de machine learning
- Comunidad de código abierto por las bibliotecas y herramientas

---

**📝 Nota**: Este README se actualiza regularmente. Para la información más reciente, consulte la [documentación completa](https://github.com/ctangarife/reto-ia-log-analyzer/wiki) o los [issues del proyecto](https://github.com/ctangarife/reto-ia-log-analyzer/issues).
