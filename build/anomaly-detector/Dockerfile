# Imagen base
FROM python:3.11-slim

# Metadatos
LABEL maintainer="logs-anomaly-team"
LABEL version="1.0"
LABEL description="Anomaly Detection Service for Log Analysis"

# Variables de entorno
ENV SERVICE_NAME=anomaly-detector
ENV SERVICE_VERSION=1.0
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para cachear dependencias
COPY data/backend-python/requirements.txt /tmp/requirements.txt

# Instalar dependencias de Python (se cachean en la imagen)
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Crear directorio para reportes
RUN mkdir -p /app/reports /app/chunks

# Nota: El código se monta como volumen desde data/backend-python/
# para desarrollo con hot-reload

# Exponer puerto
EXPOSE 8000

# Comando por defecto (puede ser sobreescrito en docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
