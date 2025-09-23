#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Iniciando pruebas del servicio de detección de anomalías${NC}"

# Verificar que los servicios estén corriendo
echo -e "\n${YELLOW}Verificando servicios...${NC}"

services=("logs-analyze-mongodb" "logs-analyze-postgres" "logs-analyze-redis" "logs-analyze-detector")
all_running=true

for service in "${services[@]}"; do
    if docker ps | grep -q $service; then
        echo -e "${GREEN}✓ $service está corriendo${NC}"
    else
        echo -e "${RED}✗ $service no está corriendo${NC}"
        all_running=false
    fi
done

if [ "$all_running" = false ]; then
    echo -e "${RED}Error: Algunos servicios no están corriendo. Ejecuta docker-compose up -d${NC}"
    exit 1
fi

# Generar datos de prueba
echo -e "\n${YELLOW}Generando datos de prueba...${NC}"
python generate_test_logs.py

# Verificar que los archivos se generaron
if [ ! -d "test_data" ]; then
    echo -e "${RED}Error: No se encontró el directorio test_data${NC}"
    exit 1
fi

# Ejecutar pruebas de procesamiento
echo -e "\n${YELLOW}Ejecutando pruebas de procesamiento...${NC}"
python test_processing.py

# Verificar resultados en MongoDB
echo -e "\n${YELLOW}Verificando resultados en MongoDB...${NC}"
docker exec logs-analyze-mongodb mongosh --eval '
    db = db.getSiblingDB("logsanomaly");
    print("Total chunks procesados: " + db.chunks.count());
    print("Total resultados: " + db.results.count());
    print("\nÚltimos 5 resultados:");
    db.results.find().sort({created_at: -1}).limit(5).forEach(printjson);
'

# Verificar estadísticas en PostgreSQL
echo -e "\n${YELLOW}Verificando estadísticas en PostgreSQL...${NC}"
docker exec logs-analyze-postgres psql -U anomaly_user -d logsanomaly -c "
    SELECT 
        status, 
        COUNT(*) as count,
        AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_processing_time
    FROM processing_jobs 
    GROUP BY status;
"

# Verificar métricas de Redis
echo -e "\n${YELLOW}Verificando métricas de Redis...${NC}"
docker exec logs-analyze-redis redis-cli INFO | grep -E "used_memory|connected_clients|total_connections_received"

echo -e "\n${GREEN}Pruebas completadas${NC}"