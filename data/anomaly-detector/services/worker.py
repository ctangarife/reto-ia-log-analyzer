import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis
import uuid
from .anomaly_detector import detect_anomalies, get_llm_explanation

class ProcessingWorker:
    def __init__(
        self,
        mongodb_client: AsyncIOMotorClient,
        postgres_session: AsyncSession,
        redis_client: aioredis.Redis,
        worker_id: str
    ):
        self.mongodb = mongodb_client
        self.postgres = postgres_session
        self.redis = redis_client
        self.worker_id = worker_id
        self.running = False

    async def start(self):
        """Inicia el worker para procesar chunks"""
        self.running = True
        while self.running:
            try:
                # Obtener siguiente chunk de la cola
                chunk_info = await self.redis.brpop("queue:chunks_to_process", timeout=1)
                if not chunk_info:
                    continue
                
                chunk_data = json.loads(chunk_info[1])
                await self._process_chunk(chunk_data)
                
            except Exception as e:
                print(f"Error en worker {self.worker_id}: {str(e)}")
                await asyncio.sleep(1)  # Evitar ciclos rápidos en caso de error

    async def stop(self):
        """Detiene el worker"""
        self.running = False

    async def _process_chunk(self, chunk_data: Dict[str, Any]):
        """Procesa un chunk individual"""
        chunk_id = chunk_data["chunk_id"]
        job_id = chunk_data["job_id"]
        
        try:
            # 1. Actualizar estado en Redis
            await self._update_chunk_status(
                chunk_id=chunk_id,
                status="processing",
                start_time=datetime.utcnow().isoformat()
            )
            
            # 2. Obtener datos del chunk de MongoDB
            chunk = await self.mongodb.chunks.find_one({"id": chunk_id})
            if not chunk:
                raise ValueError(f"Chunk {chunk_id} no encontrado")
            
            # 3. Procesar el chunk
            log_entries = chunk["data"].split('\n')
            total_entries = len(log_entries)
            
            # Procesar en mini-batches para streaming más granular
            batch_size = 100
            anomalies = []
            
            for i in range(0, total_entries, batch_size):
                batch = log_entries[i:i + batch_size]
                anomaly_labels, anomaly_scores = detect_anomalies(batch)
                
                batch_anomalies = []
                for j, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                    if label == -1:  # Es una anomalía
                        explanation = await get_llm_explanation(batch[j])
                        anomaly = {
                            "log_entry": batch[j],
                            "score": float(score),
                            "explanation": explanation
                        }
                        batch_anomalies.append(anomaly)
                        anomalies.extend(batch_anomalies)
                
                # Publicar progreso del batch
                progress = min(100, (i + batch_size) / total_entries * 100)
                await self.redis.publish(
                    f"stream:job:{job_id}",
                    json.dumps({
                        "type": "batch_progress",
                        "chunk_id": chunk_id,
                        "chunk_number": chunk_data["chunk_number"],
                        "progress": progress,
                        "anomalies": batch_anomalies,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
            
            # 4. Guardar resultados en MongoDB
            result = {
                "chunk_id": chunk_id,
                "job_id": job_id,
                "anomalies": anomalies,
                "processing_time": None,  # Se actualiza al final
                "created_at": datetime.utcnow()
            }
            await self.mongodb.results.insert_one(result)
            
            # 5. Actualizar estadísticas en PostgreSQL
            await self._update_processing_stats(
                job_id=job_id,
                chunk_number=chunk_data["chunk_number"],
                anomalies_found=len(anomalies)
            )
            
            # 6. Marcar chunk como procesado
            await self.mongodb.chunks.update_one(
                {"id": chunk_id},
                {"$set": {"processed": True}}
            )
            
            # 7. Actualizar estado final en Redis
            await self._update_chunk_status(
                chunk_id=chunk_id,
                status="completed",
                end_time=datetime.utcnow().isoformat()
            )
            
            # 8. Verificar si es el último chunk
            await self._check_job_completion(job_id)
            
        except Exception as e:
            # En caso de error, actualizar estados
            await self._update_chunk_status(
                chunk_id=chunk_id,
                status="failed",
                error=str(e)
            )
            raise e

    async def _update_chunk_status(
        self,
        chunk_id: str,
        status: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Actualiza el estado de un chunk en Redis"""
        status_data = {"status": status}
        if start_time:
            status_data["start_time"] = start_time
        if end_time:
            status_data["end_time"] = end_time
        if error:
            status_data["error"] = error
        
        await self.redis.hset(
            f"processing:chunk:{chunk_id}",
            mapping=status_data
        )

    async def _update_processing_stats(
        self,
        job_id: str,
        chunk_number: int,
        anomalies_found: int
    ):
        """Actualiza estadísticas de procesamiento en PostgreSQL"""
        query = """
        INSERT INTO processing_stats 
        (id, job_id, chunk_number, anomalies_found, created_at)
        VALUES ($1, $2, $3, $4, NOW())
        """
        await self.postgres.execute(
            query,
            str(uuid.uuid4()),
            job_id,
            chunk_number,
            anomalies_found
        )
        
        # Actualizar contador en el job
        query = """
        UPDATE processing_jobs
        SET chunks_processed = chunks_processed + 1
        WHERE id = $1
        """
        await self.postgres.execute(query, job_id)
        await self.postgres.commit()

    async def _check_job_completion(self, job_id: str):
        """Verifica si todos los chunks de un job han sido procesados"""
        query = """
        SELECT total_chunks, chunks_processed
        FROM processing_jobs
        WHERE id = $1
        """
        result = await self.postgres.execute(query, job_id)
        job_info = result.first()
        
        if job_info["chunks_processed"] >= job_info["total_chunks"]:
            # Todos los chunks procesados, actualizar job
            query = """
            UPDATE processing_jobs
            SET status = 'completed',
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
            """
            await self.postgres.execute(query, job_id)
            await self.postgres.commit()
            
            # Publicar evento de completado
            await self.redis.publish(
                f"stream:job:{job_id}",
                json.dumps({
                    "type": "job_completed",
                    "job_id": job_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )