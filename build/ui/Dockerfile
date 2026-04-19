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

# NOTA: Ejecutamos como root para poder escribir en volúmenes montados
# El volumen ./data/frontend:/app se monta con permisos del host
# Para desarrollo, permitimos escritura como root

# Exponer puerto
EXPOSE 3000
