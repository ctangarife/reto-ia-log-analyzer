#!/bin/bash
# Script de inicio completo para el proyecto Logs Anomaly Detector

echo "🚀 Iniciando Logs Anomaly Detector..."

# Verificar que Docker esté corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    exit 1
fi

echo "✅ Docker está corriendo"

# Construir y levantar servicios
echo "🔨 Construyendo y levantando servicios..."
docker-compose up -d --build

if [ $? -ne 0 ]; then
    echo "❌ Error al levantar los servicios"
    exit 1
fi

echo "✅ Servicios levantados exitosamente"

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."

# Esperar a que Ollama esté listo
echo "   Esperando a Ollama..."
until curl -f http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "   Ollama no está listo aún, esperando..."
    sleep 5
done

# Esperar a que Anomaly Detector esté listo
echo "   Esperando a Anomaly Detector..."
until curl -f http://localhost:8000/health > /dev/null 2>&1; do
    echo "   Anomaly Detector no está listo aún, esperando..."
    sleep 5
done

echo "✅ Todos los servicios están listos"

# El modelo se descarga automáticamente via init-ollama.sh
echo "📥 El modelo se configura automáticamente al iniciar el contenedor"

echo ""
echo "🎉 ¡Proyecto iniciado exitosamente!"
echo ""
echo "📊 Servicios disponibles:"
echo "   - Anomaly Detector: http://localhost:8000"
echo "   - Ollama: http://localhost:11434"
echo ""
echo "🧪 Para probar:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:11434/api/tags"
echo ""
echo "📖 Ver logs:"
echo "   docker-compose logs -f"
