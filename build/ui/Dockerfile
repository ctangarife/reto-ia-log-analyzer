# Imagen base
FROM node:20-alpine

# Metadatos
LABEL maintainer="logs-anomaly-team"
LABEL version="1.0"
LABEL description="Frontend Build Service - Vue 3 + Vite"

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias adicionales si son necesarias
# RUN apk add --no-cache ...

# Crear usuario non-root
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Dar permisos al directorio de trabajo
RUN chown -R appuser:appuser /app

# Cambiar al usuario non-root
USER appuser

# Exponer puerto
EXPOSE 3000
