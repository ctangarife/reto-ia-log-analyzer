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

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para reportes
RUN mkdir -p /app/reports

# Nota: El código se monta como volumen desde data/anomaly-detector/
# Las dependencias se instalan en tiempo de ejecución via docker-compose

# Exponer puerto
EXPOSE 8000

