# 🚀 Guía de Pruebas con Warp

## 📋 Descripción
Este documento describe cómo ejecutar las pruebas del detector de anomalías usando Warp y capturar los resultados para análisis.

## 🎯 Comandos Principales

### 1. Ejecutar Prueba Básica (1MB)
```bash
# Ejecutar y capturar resultados
docker exec -it logs-analyze-detector bash -c "python /app/scripts/test_processing.py 2>&1 | tee /app/test_results/test_run_$(date +%Y%m%d_%H%M%S).log"
```

### 2. Ejecutar Suite Completa de Pruebas
```bash
# Ejecutar todas las pruebas y capturar resultados
docker exec -it logs-analyze-detector bash -c "
mkdir -p /app/test_results && 
python /app/scripts/generate_test_logs.py && 
python /app/scripts/test_processing.py 2>&1 | tee /app/test_results/full_test_$(date +%Y%m%d_%H%M%S).log"
```

### 3. Ver Resultados
```bash
# Listar archivos de resultados
docker exec -it logs-analyze-detector ls -l /app/test_results/

# Ver último resultado
docker exec -it logs-analyze-detector bash -c "cat \$(ls -t /app/test_results/*.log | head -1)"
```

## 📊 Estructura de Resultados

Los archivos de resultados contendrán:
- Timestamp de ejecución
- Detalles de generación de logs
- Progreso de procesamiento
- Anomalías detectadas
- Estadísticas de rendimiento
- Errores (si los hay)

## 🔍 Análisis de Resultados

### Formato de Salida
```
=== Prueba: {timestamp} ===
Archivo: {nombre_archivo}
Tamaño: {tamaño_mb} MB
Tiempo total: {tiempo} segundos
Tasa de procesamiento: {mb_por_segundo} MB/s
Total anomalías: {num_anomalías}
```

### Ejemplos de Anomalías
```
Ejemplo de anomalía:
  Log: {entrada_log}
  Score: {puntuación}
  Explicación: {explicación_llm}
```

## 🚨 Solución de Problemas

### Problemas Comunes
1. **Error de conexión WebSocket**
   - Verificar que el servicio esté corriendo
   - Comprobar la red de Docker

2. **Error de generación de logs**
   - Verificar permisos en /app/test_data
   - Comprobar espacio en disco

3. **Error de procesamiento**
   - Revisar logs de MongoDB/PostgreSQL/Redis
   - Verificar conexiones entre servicios

## 📝 Notas Adicionales

- Los resultados se guardan en `/app/test_results/`
- Cada ejecución genera un archivo único con timestamp
- Se mantiene historial de ejecuciones para comparación
- Los archivos de log incluyen tanto stdout como stderr
