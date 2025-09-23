# 🎯 Contexto del Proyecto LogsAnomaly

## 📋 Resumen Ejecutivo

**LogsAnomaly** es un sistema de detección de anomalías en logs que combina Machine Learning con IA local para identificar y explicar comportamientos sospechosos. El sistema está siendo optimizado para manejar archivos de logs masivos (35MB - 2GB).

---

## 🏗️ Nueva Arquitectura Multi-DB

### **Stack Tecnológico Actualizado**
- **Backend**: FastAPI (Python 3.11)
- **Frontend**: Vue 3 + TypeScript + PrimeVue
- **IA/ML**: Ollama + Nidum-Gemma-2B-Uncensored-GGUF
- **Bases de Datos**:
  - MongoDB (logs masivos)
  - PostgreSQL (metadatos)
  - Redis (cache y colas)
- **Containerización**: Docker + Docker Compose
- **Proxy**: Nginx

### **Arquitectura de Base de Datos**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    MongoDB      │    │   PostgreSQL    │    │     Redis       │
│  (Logs Raw)     │    │  (Metadatos)    │    │(Cache y Colas)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                               │
                    ┌─────────────────┐
                    │ Anomaly Detector│
                    │   (FastAPI)     │
                    └─────────────────┘
```

---

## 🔄 Flujo de Procesamiento Optimizado

### **1. Ingesta de Datos**
- Archivos de hasta 2GB
- División en chunks de 1MB
- Almacenamiento en MongoDB
- Tracking en PostgreSQL

### **2. Procesamiento Paralelo**
- 4-8 workers simultáneos
- Cola de procesamiento en Redis
- Cache de patrones comunes
- Resultados incrementales

### **3. Almacenamiento**
- **MongoDB**: Logs raw y chunks
- **PostgreSQL**: Metadatos y control
- **Redis**: Cache y estado

---

## 📁 Estructura de Datos Optimizada

### **MongoDB**
```javascript
// Colección: chunks
{
  "_id": ObjectId,
  "file_id": "uuid",
  "chunk_number": 1,
  "data": "contenido del chunk",
  "size": 1048576,  // 1MB
  "processed": false,
  "created_at": ISODate
}

// Colección: results
{
  "_id": ObjectId,
  "chunk_id": ObjectId,
  "anomalies": [{
    "log_entry": "texto del log",
    "score": -0.15,
    "explanation": "explicación"
  }],
  "processing_time": 123,
  "created_at": ISODate
}
```

### **PostgreSQL**
```sql
-- Tabla: processing_jobs
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    total_size BIGINT,
    total_chunks INTEGER,
    chunks_processed INTEGER,
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Tabla: processing_stats
CREATE TABLE processing_stats (
    id UUID PRIMARY KEY,
    job_id UUID,
    chunk_number INTEGER,
    processing_time FLOAT,
    anomalies_found INTEGER,
    created_at TIMESTAMP
);
```

### **Redis**
```redis
# Colas y Cache
processing:job:{id}:status -> hash
processing:job:{id}:progress -> string
queue:chunks_to_process -> list
cache:pattern:{hash} -> string
```

---

## 🐳 Configuración Docker Optimizada

### **Docker Compose**
```yaml
services:
  mongodb:
    image: mongo:7.0
    volumes:
      - mongodb_data:/data/db
    
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  anomaly-detector:
    build: ./
    depends_on:
      - mongodb
      - postgres
      - redis
```

---

## 📊 Métricas y Rendimiento

### **Capacidades de Procesamiento**
- **Archivos**: Hasta 2GB
- **Chunks**: 1MB por chunk
- **Workers**: 4-8 paralelos
- **Memoria**: 16GB recomendado

### **Tiempos Esperados**
- **500MB**: ~5 minutos
- **1GB**: ~10 minutos
- **2GB**: ~20-30 minutos

---

## 🔧 Configuraciones

### **MongoDB**
```javascript
// Índices optimizados
db.chunks.createIndex({"file_id": 1, "chunk_number": 1})
db.chunks.createIndex({"processed": 1})
db.results.createIndex({"chunk_id": 1})
```

### **PostgreSQL**
```sql
-- Índices para consultas frecuentes
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_filename ON processing_jobs(filename);
CREATE INDEX idx_stats_job_id ON processing_stats(job_id);
```

### **Redis**
```redis
# Configuración de persistencia
save 900 1
save 300 10
save 60 10000
maxmemory 8gb
maxmemory-policy allkeys-lru
```

---

## 🎯 Estado de Implementación

### ✅ **Completado**
- Arquitectura base
- Procesamiento básico
- UI inicial

### 🔄 **En Progreso**
- Migración a Multi-DB
- Sistema de chunks
- Procesamiento paralelo

### 📋 **Pendiente**
- Optimización de índices
- Fine-tuning de workers
- Dashboard de monitoreo

---

## 🚀 Próximos Pasos

1. **Implementar MongoDB** para logs masivos
2. **Configurar PostgreSQL** para metadatos
3. **Integrar Redis** para cache
4. **Optimizar procesamiento** paralelo
5. **Mejorar UI** para archivos grandes

---

**Última actualización**: 11 de enero de 2025  
**Versión**: 1.1.0  
**Estado**: En optimización para archivos masivos