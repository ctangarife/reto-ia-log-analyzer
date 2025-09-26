# Configuración Detallada de Modelos LLM

Este documento proporciona ejemplos específicos de cómo configurar diferentes modelos de lenguaje con el detector de anomalías.

## Modelos Recomendados por Tipo de Hardware

### Para sistemas con GPU NVIDIA (16GB+ VRAM)
```yaml
# docker-compose.yml
environment:
  - MODEL_NAME=llama3:8b
  - OLLAMA_DEVICE=nvidia
  - OLLAMA_GPU_LAYERS=32

deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [ gpu ]
    limits:
      memory: 32G
```

### Para sistemas con GPU NVIDIA (8-12GB VRAM)
```yaml
environment:
  - MODEL_NAME=gemma:7b
  - OLLAMA_DEVICE=nvidia
  - OLLAMA_GPU_LAYERS=24

deploy:
  resources:
    limits:
      memory: 16G
```

### Para sistemas sin GPU (Solo CPU)
```yaml
environment:
  - MODEL_NAME=phi3:mini
  - OLLAMA_DEVICE=cpu

# Comentar o eliminar sección de GPU
# deploy:
#   resources:
#     reservations:
#       devices: ...
```

## Comparación de Modelos

| Modelo | Tamaño | Recursos Mínimos | Calidad | Velocidad | Uso Recomendado |
|--------|--------|------------------|---------|-----------|-----------------|
| `phi3:mini` | ~2GB | 8GB RAM | Básica | Rápido | Desarrollo/Testing |
| `qwen2.5:3b` | ~2GB | 8GB RAM | Buena | Rápido | Uso general |
| `gemma:7b` | ~4GB | 12GB RAM/GPU | Muy buena | Medio | Producción |
| `llama3:8b` | ~4.7GB | 16GB RAM/GPU | Excelente | Lento | Alta calidad |

## Configuración Paso a Paso

### 1. Cambiar Modelo Básico

Edite las siguientes líneas en `docker-compose.yml`:

```yaml
# Servicio anomaly-detector
environment:
  - MODEL_NAME=nuevo-modelo:tag

# Servicio ollama-service  
environment:
  - OLLAMA_MODEL=nuevo-modelo:tag
```

### 2. Aplicar Cambios

```bash
# Detener servicios
docker-compose down

# Reiniciar servicios
docker-compose up -d

# Monitorear descarga del modelo
docker-compose logs -f ollama-service
```

### 3. Verificar Modelo Activo

```bash
# Ver modelos disponibles
docker exec logs-analyze-ollama ollama list

# Probar el modelo
docker exec logs-analyze-ollama ollama run modelo-name "Hola, ¿funcionas correctamente?"
```

## Modelos Especializados

### Para logs en español
```yaml
environment:
  - MODEL_NAME=llama3:8b  # Excelente soporte multiidioma
```

### Para análisis técnico detallado
```yaml
environment:
  - MODEL_NAME=deepseek-coder:6.7b  # Especializado en código
```

### Para sistemas con recursos muy limitados
```yaml
environment:
  - MODEL_NAME=tinyllama:1b
  - OLLAMA_DEVICE=cpu
```

## Configuración Avanzada

### Crear un Modelo Personalizado

1. Crear Modelfile:
```bash
# Conectar al contenedor
docker exec -it logs-analyze-ollama bash

# Crear Modelfile
cat > /tmp/Modelfile << 'EOF'
FROM llama3:8b

# Temperatura más baja para respuestas más consistentes
PARAMETER temperature 0.3

# Contexto optimizado para logs
SYSTEM """Eres un experto en análisis de logs y seguridad informática. 
Analiza logs de manera concisa y técnica, identificando:
- Patrones anómalos específicos
- Posibles amenazas de seguridad
- Recomendaciones de acción

Responde en español de forma clara y directa."""

# Tokens de parada para evitar respuestas largas
PARAMETER stop "Usuario:"
PARAMETER stop "---"
EOF

# Crear el modelo
ollama create logs-analyzer -f /tmp/Modelfile

# Probar el modelo
ollama run logs-analyzer "Analiza este log: ERROR 404 /admin/login from 192.168.1.100"

# Salir
exit
```

2. Actualizar docker-compose.yml:
```yaml
environment:
  - MODEL_NAME=logs-analyzer
  - OLLAMA_MODEL=logs-analyzer
```

### Optimización de Rendimiento

Para mejorar el rendimiento, agregue estas configuraciones:

```yaml
# En el servicio ollama-service
environment:
  - OLLAMA_NUM_PARALLEL=2      # Procesamiento paralelo
  - OLLAMA_MAX_LOADED_MODELS=1 # Un solo modelo en memoria
  - OLLAMA_FLASH_ATTENTION=1   # Optimización de atención (si compatible)
```

## Troubleshooting de Modelos

### Problema: "Modelo no encontrado"
```bash
# Verificar modelos disponibles en Ollama Hub
docker exec logs-analyze-ollama ollama list --remote

# Descargar modelo específico
docker exec logs-analyze-ollama ollama pull modelo-deseado:tag
```

### Problema: "Out of memory durante inferencia"
Soluciones:
1. Reducir modelo a uno más pequeño
2. Ajustar límites de memoria:
```yaml
deploy:
  resources:
    limits:
      memory: 8G  # Reducir límite
```

### Problema: "Respuestas lentas"
1. Verificar uso de GPU:
```bash
# Si tiene NVIDIA GPU
nvidia-smi

# Verificar que Ollama esté usando GPU
docker exec logs-analyze-ollama ollama ps
```

2. Usar modelo más pequeño temporalmente para testing

### Problema: "Respuestas en idioma incorrecto"
Crear modelo personalizado con instrucciones específicas de idioma (ver sección anterior).

## Configuraciones Preestablecidas

### Configuración "Desarrollo" (Rápido)
```yaml
environment:
  - MODEL_NAME=phi3:mini
  - OLLAMA_DEVICE=cpu
```

### Configuración "Producción" (Balanceado)
```yaml
environment:
  - MODEL_NAME=qwen2.5:3b
  - OLLAMA_DEVICE=nvidia
```

### Configuración "Alta Calidad" (Lento)
```yaml
environment:
  - MODEL_NAME=llama3:8b
  - OLLAMA_DEVICE=nvidia
  - OLLAMA_GPU_LAYERS=35
```

## Scripts de Automatización

### Script para cambiar modelo rápidamente:

```bash
#!/bin/bash
# cambiar-modelo.sh

if [ -z "$1" ]; then
    echo "Uso: ./cambiar-modelo.sh <nombre-modelo>"
    echo "Ejemplo: ./cambiar-modelo.sh llama3:8b"
    exit 1
fi

NUEVO_MODELO=$1

echo "Cambiando modelo a: $NUEVO_MODELO"

# Detener servicios
docker-compose down

# Editar docker-compose.yml (requiere sed o edición manual)
sed -i "s/MODEL_NAME=.*/MODEL_NAME=$NUEVO_MODELO/" docker-compose.yml
sed -i "s/OLLAMA_MODEL=.*/OLLAMA_MODEL=$NUEVO_MODELO/" docker-compose.yml

# Reiniciar
docker-compose up -d

echo "Cambio completado. Monitoreando logs:"
docker-compose logs -f ollama-service
```

## Monitoreo de Modelos

### Verificar estado del modelo:
```bash
# Estado general
docker exec logs-analyze-ollama ollama ps

# Uso de recursos
docker stats logs-analyze-ollama

# Logs del servicio
docker logs logs-analyze-ollama --tail 50
```

### Métricas de rendimiento:
```bash
# Tiempo de respuesta (aproximado)
time docker exec logs-analyze-ollama ollama run $MODEL_NAME "Analiza: Error 500"
```