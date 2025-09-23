#!/bin/bash
set -e

echo "Iniciando script de configuración de Ollama..."

# Configurar parámetros de GPU si están disponibles
if [ -n "$OLLAMA_DEVICE" ] && [ "$OLLAMA_DEVICE" = "nvidia" ]; then
    echo "Configurando para GPU NVIDIA"
    export CUDA_VISIBLE_DEVICES=0
    export OLLAMA_GPU_LAYERS=32
fi

# Iniciar el servicio Ollama en segundo plano
echo "Iniciando servicio Ollama..."
ollama serve &
SERVER_PID=$!

# Esperar a que el servicio esté disponible
echo "Esperando a que el servicio Ollama esté listo..."
MAX_RETRIES=30
RETRY_COUNT=0

while ! curl -s http://localhost:11434/api/version > /dev/null && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Esperando a Ollama... intento $((RETRY_COUNT+1))/$MAX_RETRIES"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Error: No se pudo conectar a Ollama después de $MAX_RETRIES intentos"
    exit 1
fi

echo "Servicio Ollama iniciado correctamente"

# Modelo a utilizar
MODEL=${OLLAMA_MODEL:-"qwen2.5:3b"}
echo "Configurando modelo: $MODEL"

echo "Listando modelos disponibles:"
ls -la /root/.ollama/models/
echo "Contenido del directorio de modelos:"
find /root/.ollama/models -type f -name "*qwen*2.5*"
find /root/.ollama/models -type f -name "*nidum*gemma*2b*"

# Detener cualquier descarga previa que pueda estar en progreso
pkill -f "ollama pull" || true
pkill -f "ollama run" || true

# Verificar si el modelo ya está registrado
if ollama list | grep -q "$MODEL"; then
    echo "Modelo $MODEL ya está registrado en Ollama"
elif [ -d "/root/.ollama/models" ]; then
    echo "Buscando modelo en el sistema de archivos..."
    
    # Buscar el modelo específico que necesitamos
    if find /root/.ollama/models -type f -name "*.gguf" | grep -q .; then
        echo "Encontrado modelo Nidum Gemma 2B en el sistema de archivos"
        MODEL_PATH=$(find /root/.ollama/models -type f -name "*.gguf" | head -n 1)
        echo "Registrando modelo desde: $MODEL_PATH"
        # Crear Modelfile temporal
        cat > /tmp/Modelfile << EOF
FROM $MODEL_PATH
PARAMETER temperature 0.7
PARAMETER stop "User:"
PARAMETER stop "Assistant:"
EOF
        # Crear modelo usando Modelfile
        ollama create "$MODEL" -f /tmp/Modelfile
        else
            echo "No se encontró el modelo en el sistema de archivos"
            echo "Descargando modelo $MODEL..."
            if [[ "$MODEL" == *"nidum"* ]]; then
                echo "Detectado modelo Nidum desde Hugging Face"
                echo "Descargando desde Hugging Face con timeout extendido..."
                timeout 600 ollama run hf.co/nidum/Nidum-Gemma-2B-Uncensored-GGUF:Q4_K_M < /dev/null &
                DOWNLOAD_PID=$!
                
                # Esperar a que termine la descarga
                echo "Esperando descarga del modelo..."
                wait $DOWNLOAD_PID
                
                # Verificar si se descargó exitosamente
                if ollama list | grep -q "hf.co/nidum/Nidum-Gemma-2B-Uncensored-GGUF:Q4_K_M"; then
                    echo "Modelo descargado exitosamente, creando alias..."
                    ollama cp hf.co/nidum/Nidum-Gemma-2B-Uncensored-GGUF:Q4_K_M $MODEL
                else
                    echo "Error: No se pudo descargar el modelo desde Hugging Face"
                    echo "Usando modelo fallback: qwen2.5:3b"
                    ollama pull qwen2.5:3b
                    ollama cp qwen2.5:3b $MODEL
                fi
            elif [[ "$MODEL" == *"qwen2.5"* ]]; then
                echo "Detectado modelo Qwen2.5, descargando desde Ollama Hub..."
                echo "Descargando $MODEL con timeout extendido..."
                timeout 600 ollama pull $MODEL
                if [ $? -eq 0 ]; then
                    echo "Modelo $MODEL descargado exitosamente"
                else
                    echo "Error: No se pudo descargar $MODEL"
                    echo "Usando modelo fallback: gemma:7b"
                    ollama pull gemma:7b
                    ollama cp gemma:7b $MODEL
                fi
            else
                echo "Descargando modelo genérico: $MODEL"
                ollama pull $MODEL
            fi
    fi
fi

# Aplicar configuración de cuantización
MODEL_PATH=$(echo $MODEL | sed 's/:/_/g')
CONFIG_PATH="/root/.ollama/models/$MODEL_PATH.json"

echo "Aplicando configuraciones de optimización a $MODEL"
cat > $CONFIG_PATH << EOF
{
  "quantization": "q4_k_m", 
  "mmap": true, 
  "context_size": 2048,
  "gpu_layers": ${OLLAMA_GPU_LAYERS:-0}
}
EOF

echo "Configuración aplicada en $CONFIG_PATH"
cat $CONFIG_PATH

echo "Configuración completada. Ollama está listo para usar."

# Mantener el proceso ollama serve en primer plano
wait $SERVER_PID