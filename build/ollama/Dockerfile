# Usa la imagen oficial de Ollama
FROM ollama/ollama:0.5.8-rc7

# Establecer directorio de trabajo
WORKDIR /root/.ollama

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para scripts
RUN mkdir -p /scripts

# Copiar script de inicialización
ADD ./build/ollama/init-ollama.sh /scripts/
RUN cat /scripts/init-ollama.sh
RUN chmod +x /scripts/init-ollama.sh

# Configuración de variables de entorno
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/root/.ollama/models

# Puerto por defecto
EXPOSE 11434

# Comando para iniciar el servicio
ENTRYPOINT ["/scripts/init-ollama.sh"]
