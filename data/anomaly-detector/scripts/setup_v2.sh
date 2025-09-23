#!/bin/bash

# Script de configuración para implementación V2
# Configura las bases de datos y verifica la implementación

echo "🚀 Configurando implementación V2 de LogsAnomaly..."
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con color
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que Docker esté ejecutándose
print_status "Verificando Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker no está ejecutándose. Por favor, inicia Docker primero."
    exit 1
fi
print_success "Docker está ejecutándose"

# Verificar que docker-compose esté disponible
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose no está instalado"
    exit 1
fi

# Navegar al directorio del proyecto
cd "$(dirname "$0")/../.."

print_status "Directorio de trabajo: $(pwd)"

# 1. Iniciar servicios de base de datos
print_status "Iniciando servicios de base de datos..."
docker-compose up -d mongodb postgres redis

# Esperar a que los servicios estén listos
print_status "Esperando a que los servicios estén listos..."
sleep 10

# 2. Configurar PostgreSQL
print_status "Configurando PostgreSQL..."
if docker-compose exec -T postgres psql -U anomaly_user -d logsanomaly -c "SELECT 1;" > /dev/null 2>&1; then
    print_success "PostgreSQL ya está configurado"
else
    print_status "Ejecutando script de inicialización de PostgreSQL..."
    docker-compose exec -T postgres psql -U postgres -f /docker-entrypoint-initdb.d/init_v2.sql
    if [ $? -eq 0 ]; then
        print_success "PostgreSQL configurado correctamente"
    else
        print_error "Error configurando PostgreSQL"
    fi
fi

# 3. Configurar MongoDB
print_status "Configurando MongoDB..."
print_status "Ejecutando script de inicialización de MongoDB..."
docker-compose exec -T mongodb mongosh -u admin -p password --authenticationDatabase admin logsanomaly < database/init_mongodb_v2.js
if [ $? -eq 0 ]; then
    print_success "MongoDB configurado correctamente"
else
    print_warning "Error configurando MongoDB (puede que ya esté configurado)"
fi

# 4. Verificar conexiones
print_status "Verificando conexiones a bases de datos..."

# Verificar MongoDB
if docker-compose exec -T mongodb mongosh -u admin -p password --authenticationDatabase admin logsanomaly --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    print_success "MongoDB: Conexión exitosa"
else
    print_error "MongoDB: Error de conexión"
fi

# Verificar PostgreSQL
if docker-compose exec -T postgres psql -U anomaly_user -d logsanomaly -c "SELECT 1;" > /dev/null 2>&1; then
    print_success "PostgreSQL: Conexión exitosa"
else
    print_error "PostgreSQL: Error de conexión"
fi

# Verificar Redis
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    print_success "Redis: Conexión exitosa"
else
    print_error "Redis: Error de conexión"
fi

# 5. Reconstruir y reiniciar el servicio anomaly-detector
print_status "Reconstruyendo servicio anomaly-detector..."
docker-compose build anomaly-detector
if [ $? -eq 0 ]; then
    print_success "Servicio reconstruido correctamente"
else
    print_error "Error reconstruyendo el servicio"
    exit 1
fi

print_status "Reiniciando servicio anomaly-detector..."
docker-compose restart anomaly-detector
if [ $? -eq 0 ]; then
    print_success "Servicio reiniciado correctamente"
else
    print_error "Error reiniciando el servicio"
    exit 1
fi

# 6. Esperar a que el servicio esté listo
print_status "Esperando a que el servicio esté listo..."
sleep 5

# 7. Verificar que el servicio esté funcionando
print_status "Verificando servicio anomaly-detector..."
if curl -s http://localhost:8000/health | grep -q "ok"; then
    print_success "Servicio anomaly-detector está funcionando"
else
    print_error "Servicio anomaly-detector no está respondiendo"
    print_status "Verificando logs del servicio..."
    docker-compose logs --tail=20 anomaly-detector
fi

# 8. Ejecutar pruebas básicas
print_status "Ejecutando pruebas básicas..."
if [ -f "test_v2_implementation.py" ]; then
    print_status "Ejecutando script de pruebas..."
    python3 test_v2_implementation.py
    if [ $? -eq 0 ]; then
        print_success "Pruebas completadas exitosamente"
    else
        print_warning "Algunas pruebas fallaron (esto puede ser normal en la primera ejecución)"
    fi
else
    print_warning "Script de pruebas no encontrado"
fi

# 9. Mostrar información de estado
print_status "Estado de los servicios:"
docker-compose ps

print_status "URLs de acceso:"
echo "  - API: http://localhost:8000"
echo "  - UI: http://localhost:3000"
echo "  - MongoDB: mongodb://admin:password@localhost:27017/logsanomaly"
echo "  - PostgreSQL: postgresql://anomaly_user:anomaly_password@localhost:5432/logsanomaly"
echo "  - Redis: redis://localhost:6379/0"

print_status "Endpoints V2 disponibles:"
echo "  - POST /api/v2/process - Procesar archivo"
echo "  - GET /api/v2/status/{job_id} - Obtener estado"
echo "  - GET /api/v2/results/{job_id}/stream - Stream de resultados"
echo "  - POST /api/v2/cancel/{job_id} - Cancelar procesamiento"

echo ""
print_success "🎉 Configuración V2 completada!"
print_status "Puedes ahora usar la nueva arquitectura multi-DB para procesar archivos masivos."
print_status "Para probar, sube un archivo a través de la UI o usa curl:"
echo "  curl -X POST http://localhost:8000/api/v2/process -F 'file=@tu_archivo.txt'"
