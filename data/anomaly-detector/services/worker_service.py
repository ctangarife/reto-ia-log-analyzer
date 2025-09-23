import asyncio
import time
import os
import sys
from typing import List, Dict, Any

# Agregar el directorio padre al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config.database import db_manager
from models.v2_models import ChunkResult, AnomalyResultV2
from services.chunk_service import chunk_service

class WorkerService:
    def __init__(self):
        self.max_workers = 4
        self.workers = []
    
    async def process_chunk(self, chunk_data: Dict[str, Any]) -> ChunkResult:
        """Procesa un chunk individual"""
        start_time = time.time()
        chunk_id = str(chunk_data["_id"])
        
        print(f"Procesando chunk {chunk_id} con {len(chunk_data['data'])} caracteres")
        
        # Extraer características y detectar anomalías
        lines = chunk_data["data"].split('\n')
        anomalies = []
        
        # Simular detección de anomalías (por ahora)
        for i, line in enumerate(lines):
            if line.strip():
                # Simular detección basada en palabras clave
                suspicious_keywords = ['error', 'failed', 'unauthorized', 'exception', 'timeout', 'denied', 'critical']
                is_suspicious = any(keyword in line.lower() for keyword in suspicious_keywords)
                
                if is_suspicious or i % 10 == 0:  # Cada 10 líneas como anomalía de prueba
                    anomaly_result = AnomalyResultV2(
                        log_entry=line,
                        score=-0.1 if is_suspicious else -0.05,
                        is_anomaly=True,
                        explanation=f"Anomalía detectada: {'Palabras sospechosas encontradas' if is_suspicious else 'Patrón inusual detectado'}",
                        chunk_id=chunk_id
                    )
                    anomalies.append(anomaly_result)
        
        processing_time = time.time() - start_time
        
        print(f"Chunk {chunk_id} procesado: {len(anomalies)} anomalías encontradas en {processing_time:.2f}s")
        
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
        
        if not chunks:
            print(f"No hay chunks para procesar para el archivo {file_id}")
            return []
        
        print(f"Procesando {len(chunks)} chunks para el archivo {file_id}")
        
        # Ejecutar con límite de workers
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(chunk):
            async with semaphore:
                return await self.process_chunk(chunk)
        
        # Crear tareas para procesamiento paralelo
        tasks = [asyncio.create_task(process_with_semaphore(chunk)) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verificar si hubo errores
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error procesando chunk {i}: {result}")
        
        # Actualizar estado del job a completado
        await self._update_job_status(file_id, "completed")
        
        return results
    
    async def _update_job_status(self, file_id: str, status: str):
        """Actualizar el estado de un job en PostgreSQL"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                if status == "completed":
                    await conn.execute("""
                        UPDATE processing_jobs 
                        SET status = $1, completed_at = $2 
                        WHERE id = $3
                    """, status, datetime.utcnow(), file_id)
                else:
                    await conn.execute("""
                        UPDATE processing_jobs 
                        SET status = $1 
                        WHERE id = $2
                    """, status, file_id)
                print(f"Estado del job {file_id} actualizado a {status}")
        except Exception as e:
            print(f"Error actualizando estado del job: {e}")

worker_service = WorkerService()
