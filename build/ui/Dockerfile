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

# Usar el usuario 'node' que ya existe en la imagen base (UID 1000)
# Dar permisos al directorio de trabajo
RUN chown -R node:node /app

# Cambiar al usuario node (ya existe en la imagen)
USER node

# Exponer puerto
EXPOSE 3000
