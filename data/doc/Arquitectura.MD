# 🏗️ Arquitectura de Proyectos con Docker

## 📋 Descripción General

Este documento describe una arquitectura estándar para proyectos que utilizan Docker Compose. La arquitectura está diseñada para ser escalable, mantenible y fácil de replicar en diferentes tipos de proyectos, no solo ELK.

## 🎯 Principios de Diseño

### 1. **Separación de Responsabilidades**
- **Build**: Contiene Dockerfiles para construcción de imágenes personalizadas
- **Data**: Almacena configuraciones y datos de aplicación
- **BD**: Persistencia de datos de bases de datos y servicios
- **Orquestación**: Docker Compose para coordinación de servicios

### 2. **Modularidad**
- Cada servicio tiene su propia configuración independiente
- Componentes reutilizables y intercambiables
- Configuraciones separadas por entorno (dev, staging, prod)

### 3. **Escalabilidad**
- Servicios independientes que pueden escalar individualmente
- Redes Docker aisladas para mejor rendimiento
- Configuración de recursos por servicio

## 🏛️ Estructura de Directorios Estándar

### Estructura General (Patrón de Referencia)
```
proyecto/
├── 📁 bd/                          # Solo datos de bases de datos
│   ├── 📁 postgres-data/           # Datos de PostgreSQL
│   ├── 📁 redis-data/              # Datos de Redis
│   └── 📁 mongodb-data/            # Datos de MongoDB
│
├── 🔨 build/                        # Solo Dockerfiles
│   ├── 📁 {service1}/              # Dockerfile para servicio 1
│   │   ├── 📄 Dockerfile           # Solo estructura base
│   │   └── 📄 init-script.sh       # Scripts de inicialización
│   ├── 📁 {service2}/              # Dockerfile para servicio 2
│   └── 📁 {service3}/              # Dockerfile para servicio 3
│
├── 📊 data/                         # Código y configuraciones
│   ├── 📁 {service1}/              # Código del servicio 1
│   │   ├── 📄 main.py              # Código principal
│   │   ├── 📄 requirements.txt     # Dependencias
│   │   └── 📁 config/              # Configuraciones
│   ├── 📁 {service2}/              # Código del servicio 2
│   ├── 📁 {service3}/              # Código del servicio 3
│   ├── 📁 scripts/                 # Scripts de utilidad
│   └── 📁 doc/                     # Documentación
│
├── 🐳 docker-compose.yml           # Orquestación de servicios
├── 🐳 docker-compose.override.yml  # Configuraciones de desarrollo
├── 🐳 docker-compose.prod.yml      # Configuraciones de producción
├── ⚙️ .env.example                 # Variables de entorno de ejemplo
├── ⚙️ .env                         # Variables de entorno (no versionado)
```

### Estructura Específica de CommentBot
```
commentbot/
├── 📁 bd/                          # Solo datos de bases de datos (vacío)
│
├── 🔨 build/                        # Solo Dockerfiles
│   ├── 📁 commentbot-core/
│   │   └── 📄 Dockerfile           # Solo estructura base (sin CMD)
│   ├── 📁 ollama/
│   │   ├── 📄 Dockerfile
│   │   └── 📄 init-ollama.sh       # Script de inicialización
│   └── 📁 whisper-service/
│       ├── 📄 Dockerfile
│       └── 📄 main.py              # Servicio Whisper
│
├── 📊 data/                         # Código y datos persistentes
│   ├── 📁 commentbot-core/          # Servicio FastAPI principal
│   │   ├── 📄 main.py              # Servicio FastAPI
│   │   └── 📄 requirements.txt     # Dependencias Python
│   ├── 📁 audio-cache/             # Cache de archivos de audio
│   ├── 📁 transcripts/             # Transcripciones y resultados
│   ├── 📁 models/ollama/           # Modelos de IA descargados
│   ├── 📁 scripts/                 # Scripts de utilidad
│   │   ├── 📄 setup.sh
│   │   ├── 📄 test.sh
│   │   ├── 📄 cleanup.sh
│   │   └── 📄 diagnostic.sh
│   └── 📁 doc/                     # Documentación técnica
│       ├── 📄 Arquitectura.MD
│       ├── 📄 Implementacion.MD
│       ├── 📄 ProyectoComment.MD
│       ├── 📄 CasosDeUso.MD
│       ├── 📄 ResumenEjecutivo.MD
│       └── 📄 README.md
│
├── 📄 main.py                      # Script CLI principal
├── 📄 test_simple.py               # Script de pruebas
├── 🐳 docker-compose.yml           # Orquestación (ejecuta desde docker-compose)
├── ⚙️ env.example                  # Variables de entorno
└── 📄 README.md                    # Documentación principal
```

## 🔄 Flujo de Datos Genérico

```
📱 Entrada → 🔄 Procesamiento → 🗄️ Almacenamiento → 📊 Visualización
     ↓              ↓                ↓                ↓
📁 Inputs    🔄 Services      📁 Databases      📊 Dashboards
     ↓              ↓                ↓                ↓
📁 Logs      🔄 Pipelines     📁 Indices        📁 Reports
```

## 🐳 Arquitectura Docker

### **Redes**
```yaml
networks:
  app-network:
    driver: bridge
    # Permite comunicación entre servicios
    # Aislamiento del resto del sistema
    # Configuración de IPs estáticas si es necesario
```

### **Volúmenes**
```yaml
volumes:
  # Configuraciones (read-only)
  - ./data/{service}/config:/etc/{service}/config:ro
  
  # Datos persistentes
  - ./bd/{service}-data:/var/lib/{service}
  
  # Logs y datos temporales
  - ./data/logs:/var/log/{service}
  
  # Archivos compartidos entre servicios
  - ./data/shared:/shared
```

### **Health Checks**
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:port/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

## 🎭 Patrón de Servicios

### **Estructura de un Servicio**
```
{service}/
├── 📄 Dockerfile                    # Construcción de imagen
├── 📄 .dockerignore                 # Archivos a excluir
├── 📄 requirements.txt              # Dependencias (si aplica)
├── 📁 config/                       # Configuraciones
├── 📁 scripts/                      # Scripts de inicialización
└── 📁 tests/                        # Tests del servicio
```

### **Dockerfile Estándar**
```dockerfile
# Imagen base
FROM {base-image}:{version}

# Metadatos
LABEL maintainer="team@company.com"
LABEL version="1.0"
LABEL description="Service description"

# Variables de entorno
ENV SERVICE_NAME={service}
ENV SERVICE_VERSION=1.0

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE {port}

# Comando de inicio
CMD ["python", "main.py"]
```

### **Servicio en Docker Compose**
```yaml
{service}:
  build:
    context: ./build/{service}
    dockerfile: Dockerfile
    args:
      - BUILD_ENV=production
  image: {service}:latest
  container_name: {service}
  environment:
    - SERVICE_NAME={service}
    - ENVIRONMENT=production
  volumes:
    - ./data/{service}/config:/etc/{service}/config:ro
    - ./bd/{service}-data:/var/lib/{service}
    - ./data/logs:/var/log/{service}
  ports:
    - "{host-port}:{container-port}"
  networks:
    - app-network
  depends_on:
    {dependency-service}:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:{port}/health"]
    interval: 30s
    timeout: 10s
    retries: 5
  restart: unless-stopped
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '0.5'
      reservations:
        memory: 512M
        cpus: '0.25'
```

## 🔧 Patrón de Configuración

### **Estructura de Configuración**
```
data/
├── 📁 {service}/
│   ├── 📄 {service}.yml              # Configuración principal
│   ├── 📁 config/                    # Configuraciones adicionales
│   ├── 📁 templates/                 # Plantillas de configuración
│   └── 📁 {custom}/                  # Archivos personalizados
```

### **Mapeo de Volúmenes**
```yaml
volumes:
  # Configuración principal
  - ./data/{service}/config/{service}.yml:/etc/{service}/{service}.yml:ro
  
  # Configuraciones adicionales
  - ./data/{service}/config:/etc/{service}/conf.d:ro
  
  # Plantillas
  - ./data/{service}/templates:/etc/{service}/templates:ro
```

## 📊 Patrón de Monitoreo

### **Script de Monitoreo**
```bash
#!/bin/bash
# monitor_{service}.sh

# Configuración
SERVICE_NAME="{service}"
HEALTH_URL="http://localhost:{port}/health"
METRICS_URL="http://localhost:{port}/metrics"
LOG_FILE="/var/log/monitor.log"

# Función de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOG_FILE"
}

# Verificar salud del servicio
if curl -f "$HEALTH_URL" > /dev/null 2>&1; then
    log "$SERVICE_NAME is healthy"
    
    # Verificar métricas
    if curl -s "$METRICS_URL" > /dev/null 2>&1; then
        log "$SERVICE_NAME metrics endpoint is accessible"
    else
        log "WARNING: $SERVICE_NAME metrics endpoint is not accessible"
    fi
else
    log "ERROR: $SERVICE_NAME is not healthy"
    exit 1
fi
```

### **Servicio de Monitoreo**
```yaml
{service}-monitor:
  image: curlimages/curl:latest
  volumes:
    - ./data/monitoring/monitor_{service}.sh:/monitor.sh:ro
    - ./data/logs:/var/log
  command: ["sh", "/monitor.sh"]
  restart: unless-stopped
  networks:
    - app-network
  depends_on:
    - {service}
```

## 🚀 Patrón de Escalado

### **Escalado Horizontal**
```yaml
# Escalar servicios individuales
docker compose up -d --scale {service}=3

# Escalar con balanceo de carga
{service}:
  deploy:
    replicas: 3
    resources:
      limits:
        memory: 1G
        cpus: '0.5'
    restart_policy:
      condition: on-failure
      delay: 5s
      max_attempts: 3
```

### **Escalado Vertical**
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 1G
      cpus: '0.5'
```

## 🔐 Patrón de Seguridad

### **Variables de Entorno**
```bash
# .env
# Configuración general
ENVIRONMENT=production
APP_VERSION=1.0.0

# Credenciales de servicios
{service1}_USER=user1
{service1}_PASSWORD=secure_password1
{service2}_USER=user2
{service2}_PASSWORD=secure_password2

# Configuración de red
NETWORK_NAME=app-network
NETWORK_DRIVER=bridge

# Recursos
{service1}_MEMORY_LIMIT=1G
{service1}_CPU_LIMIT=0.5
```

### **Configuración de Seguridad**
```yaml
environment:
  # Habilitar seguridad
  - SECURITY_ENABLED=true
  - SSL_ENABLED=true
  
  # Configuración de autenticación
  - AUTH_TYPE=jwt
  - JWT_SECRET=${JWT_SECRET}
  
  # Configuración de red
  - BIND_ADDRESS=0.0.0.0
  - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
```

## 📈 Patrón de Logging

### **Estructura de Logs**
```json
{
  "@timestamp": "2025-01-01T12:00:00Z",
  "level": "INFO",
  "service": "service-name",
  "version": "1.0.0",
  "environment": "production",
  "message": "Log message",
  "metadata": {
    "user_id": "12345",
    "request_id": "req-67890",
    "duration_ms": 150,
    "ip_address": "192.168.1.100"
  },
  "context": {
    "function": "process_request",
    "line": 45,
    "file": "main.py"
  }
}
```

### **Configuración de Logging**
```yaml
# En docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service={service}"
    env: "ENVIRONMENT"
```

## 🎯 Casos de Uso de la Arquitectura

### **1. Aplicación Web con Microservicios**
- Servicios independientes para cada funcionalidad
- Base de datos compartida o separada
- API Gateway para enrutamiento
- Load balancer para escalabilidad

### **2. Sistema de Análisis de Datos**
- Servicios de ingesta de datos
- Procesamiento en batch y tiempo real
- Almacenamiento distribuido
- Dashboards de visualización

### **3. Sistema de Monitoreo y Observabilidad**
- Agentes de recolección de métricas
- Servicios de procesamiento y alertas
- Base de datos de series temporales
- Interfaces de visualización

### **4. Plataforma de Machine Learning**
- Servicios de entrenamiento de modelos
- Servicios de inferencia
- Almacenamiento de datos y modelos
- Monitoreo de rendimiento

## 🔄 Pasos para Replicar la Arquitectura

### **1. Crear Estructura Base**
```bash
# Crear directorios principales
mkdir -p {bd,build,data}

# Crear estructura para cada servicio
for service in service1 service2 service3; do
    mkdir -p bd/${service}-data
    mkdir -p build/${service}
    mkdir -p data/${service}/{config,templates,scripts}
done

# Crear directorios adicionales
mkdir -p data/{monitoring,scripts,shared}
```

### **2. Copiar Patrones de Dockerfile**
```bash
# Para cada servicio
for service in service1 service2 service3; do
    cp -r build/{service}/ Dockerfile
    # Adaptar para el nuevo servicio
    sed -i "s/{service}/$service/g" Dockerfile
done
```

### **3. Configurar Docker Compose**
```yaml
# Crear docker-compose.yml base
version: '3.8'

services:
  # Agregar servicios uno por uno
  {service1}:
    build:
      context: ./build/{service1}
      dockerfile: Dockerfile
    # Configurar volúmenes, redes y dependencias

networks:
  app-network:
    driver: bridge
```

### **4. Implementar Health Checks**
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:{port}/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

### **5. Configurar Monitoreo**
```bash
# Crear script de monitoreo para cada servicio
for service in service1 service2 service3; do
    cat > data/monitoring/monitor_${service}.sh << 'EOF'
#!/bin/bash
# monitor_${service}.sh
# Implementar verificaciones de salud
EOF
    chmod +x data/monitoring/monitor_${service}.sh
done
```

## 📚 Mejores Prácticas

### **1. Nomenclatura**
- Usar nombres descriptivos y consistentes
- Seguir convenciones de Docker (lowercase, hyphens)
- Mantener versiones en tags semánticos
- Usar prefijos para identificar entornos

### **2. Configuración**
- Separar configuraciones por entorno
- Usar variables de entorno para secretos
- Documentar todas las opciones de configuración
- Implementar validación de configuración

### **3. Monitoreo**
- Implementar health checks para todos los servicios
- Crear métricas de rendimiento
- Configurar alertas automáticas
- Implementar logging estructurado

### **4. Seguridad**
- Usar redes aisladas
- Implementar autenticación y autorización
- Rotar credenciales regularmente
- Escanear imágenes en busca de vulnerabilidades

### **5. Mantenimiento**
- Usar tags específicos de versión
- Implementar backups automáticos
- Documentar procedimientos de actualización
- Implementar rollback automático

## 🔍 Consideraciones de Rendimiento

### **Recursos del Sistema**
- **Mínimo**: 4GB RAM, 2 CPU cores
- **Recomendado**: 8GB RAM, 4 CPU cores
- **Producción**: 16GB+ RAM, 8+ CPU cores

### **Optimizaciones**
- Usar imágenes base optimizadas
- Implementar multi-stage builds
- Configurar límites de recursos apropiados
- Implementar caché de capas Docker

### **Monitoreo de Recursos**
```bash
# Ver uso de recursos
docker stats

# Ver logs de rendimiento
docker compose logs -f {service}

# Analizar uso de recursos
docker system df
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

## 🛠️ Herramientas de Desarrollo

### **Scripts de Utilidad**
```bash
# scripts/dev-setup.sh
#!/bin/bash
# Configuración del entorno de desarrollo

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Archivo .env creado desde .env.example"
fi

# Construir imágenes
docker compose build

# Levantar servicios
docker compose up -d

echo "Entorno de desarrollo configurado"
```

### **Scripts de Producción**
```bash
# scripts/prod-deploy.sh
#!/bin/bash
# Despliegue en producción

# Verificar variables de entorno
if [ -z "$ENVIRONMENT" ]; then
    echo "ERROR: ENVIRONMENT no está definida"
    exit 1
fi

# Desplegar con configuración de producción
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "Despliegue en producción completado"
```

---

**Esta arquitectura está diseñada para ser flexible, escalable y fácil de replicar. Adapta los patrones según las necesidades específicas de tu proyecto y el tipo de aplicación que estés desarrollando.**
