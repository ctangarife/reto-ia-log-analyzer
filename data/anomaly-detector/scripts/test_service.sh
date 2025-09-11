#!/bin/bash
# Script para probar el servicio anomaly-detector

echo "🧪 Probando servicio Anomaly Detector..."

# Verificar que el servicio esté corriendo
echo "📡 Verificando health check..."
curl -f http://localhost:8000/health || {
    echo "❌ Error: El servicio no está respondiendo"
    exit 1
}

echo "✅ Health check exitoso"

# Crear archivo de logs de prueba
echo "📝 Creando archivo de logs de prueba..."
cat > /tmp/test_logs.txt << 'EOF'
2024-01-01 10:00:00 INFO User login successful
2024-01-01 10:01:00 INFO Database connection established
2024-01-01 10:02:00 ERROR Failed to connect to external API
2024-01-01 10:03:00 INFO User logout successful
2024-01-01 10:04:00 CRITICAL System memory usage exceeded 95%
2024-01-01 10:05:00 INFO Backup process completed
2024-01-01 10:06:00 WARNING High CPU usage detected
2024-01-01 10:07:00 ERROR Unauthorized access attempt from IP 192.168.1.100
2024-01-01 10:08:00 INFO Scheduled task executed successfully
2024-01-01 10:09:00 FATAL Database corruption detected
EOF

# Probar detección de anomalías
echo "🔍 Probando detección de anomalías..."
curl -X POST "http://localhost:8000/detect" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/tmp/test_logs.txt" \
     -o /tmp/anomaly_results.json

if [ $? -eq 0 ]; then
    echo "✅ Detección de anomalías exitosa"
    echo "📊 Resultados:"
    cat /tmp/anomaly_results.json | jq '.' 2>/dev/null || cat /tmp/anomaly_results.json
else
    echo "❌ Error en detección de anomalías"
    exit 1
fi

# Limpiar archivos temporales
rm -f /tmp/test_logs.txt /tmp/anomaly_results.json

echo "🎉 Pruebas completadas exitosamente"
