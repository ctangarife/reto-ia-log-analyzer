#!/bin/bash
# Script de inicio completo para el proyecto Logs Anomaly Detector
# Compatible con Docker y Podman

echo "🚀 Iniciando Logs Anomaly Detector..."

# Detectar si usar Podman o Docker
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    COMPOSE_CMD="podman-compose"
    echo "📦 Usando Podman"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    COMPOSE_CMD="docker-compose"
    echo "📦 Usando Docker"
else
    echo "❌ Error: Ni Docker ni Podman están instalados"
    exit 1
fi

# Verificar que el motor de contenedores esté funcionando
if ! $CONTAINER_CMD info > /dev/null 2>&1; then
    echo "❌ Error: $CONTAINER_CMD no está funcionando"
    exit 1
fi

echo "✅ $CONTAINER_CMD está funcionando"

# Verificar que exista el archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado, copiando desde env.template..."
    cp env.template .env
    echo "⚠️  Por favor edita el archivo .env con tus configuraciones antes de continuar"
    exit 1
fi

# Construir y levantar servicios
echo "🔨 Construyendo y levantando servicios..."
$COMPOSE_CMD up -d --build

if [ $? -ne 0 ]; then
    echo "❌ Error al levantar los servicios"
    exit 1
fi

echo "✅ Servicios levantados exitosamente"

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."

# Esperar a que PostgreSQL esté listo
echo "   Esperando a PostgreSQL..."
until $CONTAINER_CMD exec logs-analyze-postgres pg_isready -U anomaly_user -d logsanomaly > /dev/null 2>&1; do
    echo "   PostgreSQL no está listo aún, esperando..."
    sleep 3
done
echo "   ✅ PostgreSQL listo"

# Esperar a que MongoDB esté listo
echo "   Esperando a MongoDB..."
until $CONTAINER_CMD exec logs-analyze-mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
    echo "   MongoDB no está listo aún, esperando..."
    sleep 3
done
echo "   ✅ MongoDB listo"

# Esperar a que Redis esté listo
echo "   Esperando a Redis..."
until $CONTAINER_CMD exec logs-analyze-redis redis-cli ping > /dev/null 2>&1; do
    echo "   Redis no está listo aún, esperando..."
    sleep 3
done
echo "   ✅ Redis listo"

# Esperar a que Anomaly Detector esté listo
echo "   Esperando a Anomaly Detector..."
until curl -f http://localhost:8000/health > /dev/null 2>&1; do
    echo "   Anomaly Detector no está listo aún, esperando..."
    sleep 5
done
echo "   ✅ Anomaly Detector listo"

echo "✅ Todos los servicios están listos"

echo ""
echo "🎉 ¡Proyecto iniciado exitosamente!"
echo ""
echo "📊 Servicios disponibles:"
echo "   - Frontend: http://localhost"
echo "   - API Backend: http://localhost:8000"
echo "   - Health Check: http://localhost/health"
echo ""
echo "🧪 Para probar:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost/health"
echo ""
echo "📖 Ver logs:"
echo "   $COMPOSE_CMD logs -f"
echo ""
echo "🛑 Para detener:"
echo "   $COMPOSE_CMD down"
