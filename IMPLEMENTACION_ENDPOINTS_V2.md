# 🚀 Guía de Implementación: Endpoints V2 para Arquitectura Multi-DB

## 📋 Resumen del Objetivo

Implementar los endpoints v2 en el servicio `anomaly-detector` para activar la arquitectura multi-DB (MongoDB + PostgreSQL + Redis) y permitir el procesamiento de archivos masivos con chunks.

---

## 🎯 Paso 1: Preparar Dependencias y Configuración

### 1.1 Actualizar requirements.txt
```bash
# Agregar al archivo data/anomaly-detector/requirements.txt:
motor==3.3.2          # MongoDB async driver
asyncpg==0.29.0       # PostgreSQL async driver  
redis==5.0.1          # Redis client
pydantic==2.5.0       # Para modelos de datos
uuid==1.30            # Para generar IDs únicos
```

### 1.2 Crear archivo de configuración de bases de datos
```bash
# Crear: data/anomaly-detector/config/database.py
```

**Contenido del archivo:**
```python
import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import redis.asyncio as redis
from typing import Optional

class DatabaseManager:
    def __init__(self):
        self.mongodb_client: Optional[AsyncIOMotorClient] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect_mongodb(self):
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://admin:password@mongodb:27017/logsanomaly")
        self.mongodb_client = AsyncIOMotorClient(mongodb_uri)
        await self.mongodb_client.admin.command('ping')
        print("✅ MongoDB conectado")
    
    async def connect_postgres(self):
        postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://anomaly_user:anomaly_password@postgres:5432/logsanomaly")
        self.postgres_pool = await asyncpg.create_pool(postgres_dsn)
        print("✅ PostgreSQL conectado")
    
    async def connect_redis(self):
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis_client = redis.from_url(redis_url)
        await self.redis_client.ping()
        print("✅ Redis conectado")
    
    async def connect_all(self):
        await self.connect_mongodb()
        await self.connect_postgres()
        await self.connect_redis()

# Instancia global
db_manager = DatabaseManager()
```

---

## 🎯 Paso 2: Crear Modelos de Datos V2

### 2.1 Crear archivo de modelos
```bash
# Crear: data/anomaly-detector/models/v2_models.py
```

**Contenido del archivo:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ChunkData(BaseModel):
    file_id: str
    chunk_number: int
    data: str
    size: int
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessingJob(BaseModel):
    id: str
    filename: str
    total_size: int
    total_chunks: int
    chunks_processed: int = 0
    status: ProcessingStatus = ProcessingStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class ProcessingStats(BaseModel):
    id: str
    job_id: str
    chunk_number: int
    processing_time: float
    anomalies_found: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnomalyResultV2(BaseModel):
    log_entry: str
    anomaly_score: float
    is_anomaly: bool
    explanation: str
    chunk_id: str

class ChunkResult(BaseModel):
    chunk_id: str
    anomalies: List[AnomalyResultV2]
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessResponseV2(BaseModel):
    job_id: str
    status: ProcessingStatus
    message: str
    total_chunks: int
    estimated_time: Optional[int] = None

class StatusResponseV2(BaseModel):
    job_id: str
    status: ProcessingStatus
    progress: float  # 0.0 a 1.0
    chunks_processed: int
    total_chunks: int
    anomalies_found: int
    estimated_remaining_time: Optional[int] = None
    error_message: Optional[str] = None

class StreamResult(BaseModel):
    chunk_number: int
    anomalies: List[AnomalyResultV2]
    progress: float
    is_complete: bool
```

---

## 🎯 Paso 3: Crear Servicios de Procesamiento

### 3.1 Crear servicio de chunks
```bash
# Crear: data/anomaly-detector/services/chunk_service.py
```

**Contenido del archivo:**
```python
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
from ..config.database import db_manager
from ..models.v2_models import ChunkData, ProcessingJob, ProcessingStats

class ChunkService:
    def __init__(self):
        self.chunk_size = 1024 * 1024  # 1MB
    
    async def create_chunks_from_file(self, file_content: str, filename: str) -> str:
        """Divide el archivo en chunks y los guarda en MongoDB"""
        file_id = str(uuid.uuid4())
        
        # Dividir en chunks respetando líneas
        lines = file_content.split('\n')
        chunks = []
        current_chunk = ""
        chunk_number = 0
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > self.chunk_size and current_chunk:
                # Guardar chunk actual
                chunk_data = ChunkData(
                    file_id=file_id,
                    chunk_number=chunk_number,
                    data=current_chunk,
                    size=len(current_chunk)
                )
                chunks.append(chunk_data.dict())
                chunk_number += 1
                current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line
        
        # Guardar último chunk si no está vacío
        if current_chunk:
            chunk_data = ChunkData(
                file_id=file_id,
                chunk_number=chunk_number,
                data=current_chunk,
                size=len(current_chunk)
            )
            chunks.append(chunk_data.dict())
        
        # Guardar chunks en MongoDB
        if chunks:
            await db_manager.mongodb_client.logsanomaly.chunks.insert_many(chunks)
        
        # Crear job en PostgreSQL
        job = ProcessingJob(
            id=file_id,
            filename=filename,
            total_size=len(file_content),
            total_chunks=len(chunks),
            status="pending"
        )
        
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_jobs (id, filename, total_size, total_chunks, status)
                VALUES ($1, $2, $3, $4, $5)
            """, job.id, job.filename, job.total_size, job.total_chunks, job.status)
        
        return file_id
    
    async def get_chunks_to_process(self, file_id: str) -> List[Dict[str, Any]]:
        """Obtiene chunks pendientes de procesar"""
        chunks = await db_manager.mongodb_client.logsanomaly.chunks.find({
            "file_id": file_id,
            "processed": False
        }).to_list(length=None)
        return chunks
    
    async def mark_chunk_processed(self, chunk_id: str, anomalies_count: int, processing_time: float):
        """Marca un chunk como procesado"""
        # Actualizar MongoDB
        await db_manager.mongodb_client.logsanomaly.chunks.update_one(
            {"_id": chunk_id},
            {"$set": {"processed": True}}
        )
        
        # Guardar estadísticas en PostgreSQL
        stats = ProcessingStats(
            id=str(uuid.uuid4()),
            job_id=chunk_id,
            chunk_number=0,  # Se puede obtener del chunk
            processing_time=processing_time,
            anomalies_found=anomalies_count
        )
        
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO processing_stats (id, job_id, chunk_number, processing_time, anomalies_found)
                VALUES ($1, $2, $3, $4, $5)
            """, stats.id, stats.job_id, stats.chunk_number, stats.processing_time, stats.anomalies_found)

chunk_service = ChunkService()
```

### 3.2 Crear servicio de workers
```bash
# Crear: data/anomaly-detector/services/worker_service.py
```

**Contenido del archivo:**
```python
import asyncio
import time
from typing import List, Dict, Any
from ..config.database import db_manager
from ..models.v2_models import ChunkResult, AnomalyResultV2
from .chunk_service import chunk_service

class WorkerService:
    def __init__(self):
        self.max_workers = 4
        self.workers = []
    
    async def process_chunk(self, chunk_data: Dict[str, Any]) -> ChunkResult:
        """Procesa un chunk individual"""
        start_time = time.time()
        chunk_id = str(chunk_data["_id"])
        
        # Extraer características y detectar anomalías
        lines = chunk_data["data"].split('\n')
        anomalies = []
        
        for line in lines:
            if line.strip():
                # Aquí iría la lógica de detección de anomalías
                # Por ahora, simular detección
                anomaly_result = AnomalyResultV2(
                    log_entry=line,
                    anomaly_score=-0.1,
                    is_anomaly=True,
                    explanation="Anomalía detectada por worker",
                    chunk_id=chunk_id
                )
                anomalies.append(anomaly_result)
        
        processing_time = time.time() - start_time
        
        # Guardar resultado en MongoDB
        result = ChunkResult(
            chunk_id=chunk_id,
            anomalies=anomalies,
            processing_time=processing_time
        )
        
        await db_manager.mongodb_client.logsanomaly.results.insert_one(result.dict())
        
        # Marcar chunk como procesado
        await chunk_service.mark_chunk_processed(chunk_id, len(anomalies), processing_time)
        
        return result
    
    async def process_file_async(self, file_id: str):
        """Procesa todos los chunks de un archivo de forma asíncrona"""
        chunks = await chunk_service.get_chunks_to_process(file_id)
        
        # Crear tareas para procesamiento paralelo
        tasks = [self.process_chunk(chunk) for chunk in chunks]
        
        # Ejecutar con límite de workers
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(chunk):
            async with semaphore:
                return await self.process_chunk(chunk)
        
        tasks = [process_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results

worker_service = WorkerService()
```

---

## 🎯 Paso 4: Implementar Endpoints V2

### 4.1 Agregar endpoints al main.py

**Agregar al final del archivo `data/anomaly-detector/main.py`:**

```python
# === IMPORTS ADICIONALES PARA V2 ===
import uuid
from datetime import datetime
from .config.database import db_manager
from .models.v2_models import (
    ProcessResponseV2, StatusResponseV2, StreamResult,
    ProcessingStatus
)
from .services.chunk_service import chunk_service
from .services.worker_service import worker_service

# === INICIALIZACIÓN DE BASES DE DATOS ===
@app.on_event("startup")
async def startup_event():
    """Inicializar conexiones a bases de datos"""
    try:
        await db_manager.connect_all()
        logger.info("✅ Todas las bases de datos conectadas")
    except Exception as e:
        logger.error(f"❌ Error conectando bases de datos: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar conexiones a bases de datos"""
    if db_manager.mongodb_client:
        db_manager.mongodb_client.close()
    if db_manager.postgres_pool:
        await db_manager.postgres_pool.close()
    if db_manager.redis_client:
        await db_manager.redis_client.close()

# === ENDPOINTS V2 ===

@app.post("/api/v2/process", response_model=ProcessResponseV2)
async def process_file_v2(file: UploadFile = File(...)):
    """Procesar archivo usando arquitectura multi-DB"""
    try:
        # Leer contenido del archivo
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Crear chunks y job
        file_id = await chunk_service.create_chunks_from_file(file_content, file.filename)
        
        # Iniciar procesamiento asíncrono
        asyncio.create_task(worker_service.process_file_async(file_id))
        
        # Actualizar estado a processing
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                UPDATE processing_jobs 
                SET status = $1, started_at = $2 
                WHERE id = $3
            """, ProcessingStatus.PROCESSING, datetime.utcnow(), file_id)
        
        return ProcessResponseV2(
            job_id=file_id,
            status=ProcessingStatus.PROCESSING,
            message="Procesamiento iniciado",
            total_chunks=len(file_content.split('\n')) // 1000  # Estimación
        )
        
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/status/{job_id}", response_model=StatusResponseV2)
async def get_status_v2(job_id: str):
    """Obtener estado de procesamiento"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            job = await conn.fetchrow("""
                SELECT * FROM processing_jobs WHERE id = $1
            """, job_id)
            
            if not job:
                raise HTTPException(status_code=404, detail="Job no encontrado")
            
            # Contar chunks procesados
            chunks_processed = await db_manager.mongodb_client.logsanomaly.chunks.count_documents({
                "file_id": job_id,
                "processed": True
            })
            
            # Contar anomalías encontradas
            anomalies_found = await db_manager.mongodb_client.logsanomaly.results.aggregate([
                {"$match": {"chunk_id": {"$regex": f"^{job_id}"}}},
                {"$unwind": "$anomalies"},
                {"$count": "total"}
            ]).to_list(length=1)
            
            anomalies_count = anomalies_found[0]["total"] if anomalies_found else 0
            
            progress = chunks_processed / job["total_chunks"] if job["total_chunks"] > 0 else 0
            
            return StatusResponseV2(
                job_id=job_id,
                status=ProcessingStatus(job["status"]),
                progress=progress,
                chunks_processed=chunks_processed,
                total_chunks=job["total_chunks"],
                anomalies_found=anomalies_count
            )
            
    except Exception as e:
        logger.error(f"Error obteniendo estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/results/{job_id}/stream")
async def stream_results_v2(job_id: str):
    """Stream de resultados en tiempo real"""
    async def generate():
        try:
            # Obtener chunks procesados
            chunks = await db_manager.mongodb_client.logsanomaly.chunks.find({
                "file_id": job_id,
                "processed": True
            }).to_list(length=None)
            
            total_chunks = await db_manager.mongodb_client.logsanomaly.chunks.count_documents({
                "file_id": job_id
            })
            
            for i, chunk in enumerate(chunks):
                # Obtener resultados del chunk
                result = await db_manager.mongodb_client.logsanomaly.results.find_one({
                    "chunk_id": str(chunk["_id"])
                })
                
                if result:
                    stream_result = StreamResult(
                        chunk_number=chunk["chunk_number"],
                        anomalies=result["anomalies"],
                        progress=(i + 1) / total_chunks,
                        is_complete=(i + 1) == total_chunks
                    )
                    
                    yield f"data: {stream_result.json()}\n\n"
                    await asyncio.sleep(0.1)  # Pequeña pausa para streaming
                    
        except Exception as e:
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/api/v2/cancel/{job_id}")
async def cancel_job_v2(job_id: str):
    """Cancelar procesamiento"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                UPDATE processing_jobs 
                SET status = $1, completed_at = $2 
                WHERE id = $3
            """, ProcessingStatus.CANCELLED, datetime.utcnow(), job_id)
        
        return {"message": "Procesamiento cancelado", "job_id": job_id}
        
    except Exception as e:
        logger.error(f"Error cancelando job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🎯 Paso 5: Actualizar UI para usar Endpoints V2

### 5.1 Actualizar analysisStore.ts

**Modificar `data/ui/src/stores/analysisStore.ts`:**

```typescript
// Agregar nuevas interfaces
export interface ProcessingJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  chunks_processed: number;
  total_chunks: number;
  anomalies_found: number;
  estimated_remaining_time?: number;
  error_message?: string;
}

export interface StreamResult {
  chunk_number: number;
  anomalies: any[];
  progress: number;
  is_complete: boolean;
}

// Agregar nuevas funciones al store
export const useAnalysisStore = defineStore('analysis', () => {
  // ... código existente ...
  
  const currentJob = ref<ProcessingJob | null>(null)
  const isStreaming = ref(false)
  
  // Nueva función para procesar con v2
  async function processFileV2(file: File): Promise<string> {
    try {
      isLoading.value = true
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch('/api/v2/process', {
        method: 'POST',
        body: formData
      })
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }
      
      const result = await response.json()
      currentJob.value = {
        job_id: result.job_id,
        status: result.status,
        progress: 0,
        chunks_processed: 0,
        total_chunks: result.total_chunks,
        anomalies_found: 0
      }
      
      return result.job_id
    } catch (error) {
      console.error('Error procesando archivo:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  // Función para obtener estado
  async function getJobStatus(jobId: string): Promise<ProcessingJob> {
    const response = await fetch(`/api/v2/status/${jobId}`)
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`)
    }
    return await response.json()
  }
  
  // Función para streaming de resultados
  async function streamResults(jobId: string, onChunk: (result: StreamResult) => void) {
    try {
      isStreaming.value = true
      const response = await fetch(`/api/v2/results/${jobId}/stream`)
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      if (!reader) return
      
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onChunk(data)
            } catch (e) {
              console.warn('Error parseando chunk:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error en streaming:', error)
    } finally {
      isStreaming.value = false
    }
  }
  
  // Función para cancelar job
  async function cancelJob(jobId: string) {
    try {
      const response = await fetch(`/api/v2/cancel/${jobId}`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error cancelando job:', error)
      throw error
    }
  }
  
  return {
    // ... exports existentes ...
    currentJob,
    isStreaming,
    processFileV2,
    getJobStatus,
    streamResults,
    cancelJob
  }
})
```

### 5.2 Crear componente de procesamiento V2

**Crear `data/ui/src/components/ProcessingV2.vue`:**

```vue
<template>
  <div class="processing-v2">
    <div v-if="currentJob" class="job-status">
      <h3>Procesando: {{ currentJob.job_id }}</h3>
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: `${currentJob.progress * 100}%` }"
        ></div>
      </div>
      <p>Progreso: {{ currentJob.chunks_processed }}/{{ currentJob.total_chunks }} chunks</p>
      <p>Anomalías encontradas: {{ currentJob.anomalies_found }}</p>
      <p>Estado: {{ currentJob.status }}</p>
      
      <button 
        v-if="currentJob.status === 'processing'" 
        @click="cancelProcessing"
        class="cancel-btn"
      >
        Cancelar
      </button>
    </div>
    
    <div v-if="streamingResults.length > 0" class="streaming-results">
      <h4>Resultados en tiempo real:</h4>
      <div 
        v-for="result in streamingResults" 
        :key="result.chunk_number"
        class="chunk-result"
      >
        <h5>Chunk {{ result.chunk_number }}</h5>
        <p>Anomalías: {{ result.anomalies.length }}</p>
        <div v-if="result.is_complete" class="complete-indicator">
          ✅ Completado
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAnalysisStore } from '../stores/analysisStore'
import type { StreamResult } from '../stores/analysisStore'

const analysisStore = useAnalysisStore()
const streamingResults = ref<StreamResult[]>([])
const statusInterval = ref<NodeJS.Timeout | null>(null)

const currentJob = computed(() => analysisStore.currentJob)

async function cancelProcessing() {
  if (currentJob.value) {
    try {
      await analysisStore.cancelJob(currentJob.value.job_id)
      console.log('Procesamiento cancelado')
    } catch (error) {
      console.error('Error cancelando:', error)
    }
  }
}

async function startStatusPolling(jobId: string) {
  statusInterval.value = setInterval(async () => {
    try {
      const status = await analysisStore.getJobStatus(jobId)
      analysisStore.currentJob = status
      
      if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
        if (statusInterval.value) {
          clearInterval(statusInterval.value)
          statusInterval.value = null
        }
      }
    } catch (error) {
      console.error('Error obteniendo estado:', error)
    }
  }, 2000)
}

async function startStreaming(jobId: string) {
  await analysisStore.streamResults(jobId, (result: StreamResult) => {
    streamingResults.value.push(result)
    console.log('Nuevo resultado:', result)
  })
}

onUnmounted(() => {
  if (statusInterval.value) {
    clearInterval(statusInterval.value)
  }
})
</script>

<style scoped>
.processing-v2 {
  padding: 20px;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  height: 100%;
  background-color: #4CAF50;
  transition: width 0.3s ease;
}

.cancel-btn {
  background-color: #f44336;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  margin-top: 10px;
}

.chunk-result {
  border: 1px solid #ddd;
  padding: 10px;
  margin: 10px 0;
  border-radius: 5px;
}

.complete-indicator {
  color: #4CAF50;
  font-weight: bold;
}
</style>
```

---

## 🎯 Paso 6: Actualizar App.vue para usar V2

**Modificar `data/ui/src/App.vue` para incluir el nuevo componente:**

```vue
<template>
  <div id="app">
    <!-- ... código existente ... -->
    
    <!-- Agregar componente de procesamiento V2 -->
    <ProcessingV2 v-if="useV2Processing" />
    
    <!-- ... resto del código ... -->
  </div>
</template>

<script setup lang="ts">
// ... imports existentes ...
import ProcessingV2 from './components/ProcessingV2.vue'

// Agregar variable para controlar qué versión usar
const useV2Processing = ref(true) // Cambiar a true para usar V2

// ... resto del código ...
</script>
```

---

## 🎯 Paso 7: Probar la Implementación

### 7.1 Comandos de prueba
```bash
# 1. Reiniciar el servicio
docker-compose restart anomaly-detector

# 2. Verificar logs
docker logs logs-analyze-detector -f

# 3. Probar endpoint v2
curl -X POST "http://localhost:8000/api/v2/process" \
     -F "file=@test_logs.txt"

# 4. Verificar estado
curl "http://localhost:8000/api/v2/status/{job_id}"

# 5. Verificar bases de datos
docker exec logs-analyze-mongodb mongosh -u admin -p password --authenticationDatabase admin logsanomaly --eval "db.chunks.countDocuments()"
docker exec logs-analyze-postgres psql -U anomaly_user -d logsanomaly -c "SELECT COUNT(*) FROM processing_jobs;"
```

### 7.2 Verificaciones esperadas
- ✅ MongoDB: Colección `chunks` con datos
- ✅ PostgreSQL: Tabla `processing_jobs` con registros
- ✅ Redis: Datos de cache y estado
- ✅ UI: Progreso en tiempo real
- ✅ Streaming: Resultados incrementales

---

## 🎯 Paso 8: Optimizaciones Adicionales

### 8.1 Configurar índices MongoDB
```javascript
// Ejecutar en MongoDB
db.chunks.createIndex({"file_id": 1, "chunk_number": 1})
db.chunks.createIndex({"processed": 1})
db.results.createIndex({"chunk_id": 1})
```

### 8.2 Configurar índices PostgreSQL
```sql
-- Ejecutar en PostgreSQL
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_filename ON processing_jobs(filename);
CREATE INDEX idx_stats_job_id ON processing_stats(job_id);
```

---

## ✅ Checklist de Implementación

- [ ] **Paso 1**: Actualizar requirements.txt
- [ ] **Paso 2**: Crear archivo database.py
- [ ] **Paso 3**: Crear modelos v2_models.py
- [ ] **Paso 4**: Crear servicios (chunk_service.py, worker_service.py)
- [ ] **Paso 5**: Implementar endpoints v2 en main.py
- [ ] **Paso 6**: Actualizar analysisStore.ts
- [ ] **Paso 7**: Crear componente ProcessingV2.vue
- [ ] **Paso 8**: Actualizar App.vue
- [ ] **Paso 9**: Probar implementación
- [ ] **Paso 10**: Configurar índices de BD

---

## 🚨 Notas Importantes

1. **Backup**: Hacer backup antes de implementar
2. **Testing**: Probar con archivos pequeños primero
3. **Logs**: Monitorear logs durante implementación
4. **Rollback**: Tener plan de rollback si algo falla
5. **Performance**: Ajustar número de workers según recursos

---

**Una vez implementado, el sistema podrá procesar archivos masivos usando la arquitectura multi-DB con chunks, workers paralelos y streaming en tiempo real.**
