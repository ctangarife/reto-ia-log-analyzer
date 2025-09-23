#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Crear directorio para resultados
mkdir -p /app/test_results

# Timestamp para el archivo de resultados
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="/app/test_results/test_run_${TIMESTAMP}.log"

# Función para logging
log() {
    echo -e "${1}" | tee -a "${RESULTS_FILE}"
}

# Cabecera
log "${YELLOW}=== Prueba de Detección de Anomalías ===${NC}"
log "Fecha: $(date)"
log "Archivo de resultados: ${RESULTS_FILE}"
log ""

# Verificar entorno
log "${YELLOW}Verificando entorno...${NC}"
if [ -d "/app/test_data" ]; then
    log "${GREEN}✓ Directorio test_data existe${NC}"
else
    log "${YELLOW}Creando directorio test_data...${NC}"
    mkdir -p /app/test_data
fi

# Generar datos de prueba
log "\n${YELLOW}Generando datos de prueba...${NC}"
python /app/scripts/generate_test_logs.py 2>&1 | tee -a "${RESULTS_FILE}"

# Ejecutar pruebas
log "\n${YELLOW}Ejecutando pruebas...${NC}"
python /app/scripts/test_processing.py 2>&1 | tee -a "${RESULTS_FILE}"

# Verificar resultados en bases de datos
log "\n${YELLOW}Verificando resultados en MongoDB...${NC}"
mongosh --quiet --eval '
    db = db.getSiblingDB("logsanomaly");
    print("Total chunks procesados: " + db.chunks.count());
    print("Total resultados: " + db.results.count());
' 2>&1 | tee -a "${RESULTS_FILE}"

log "\n${YELLOW}Verificando resultados en PostgreSQL...${NC}"
PGPASSWORD=anomaly_password psql -h postgres -U anomaly_user -d logsanomaly -c "
    SELECT 
        status, 
        COUNT(*) as count,
        AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_processing_time
    FROM processing_jobs 
    GROUP BY status;
" 2>&1 | tee -a "${RESULTS_FILE}"

# Resumen final
log "\n${YELLOW}=== Resumen de la Prueba ===${NC}"
log "Timestamp: ${TIMESTAMP}"
log "Resultados guardados en: ${RESULTS_FILE}"
log "Para ver los resultados completos:"
log "cat ${RESULTS_FILE}"
