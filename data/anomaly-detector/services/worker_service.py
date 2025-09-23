import asyncio
import time
import os
import sys
import re
import json
from datetime import datetime
from typing import List, Dict, Any

# Agregar el directorio padre al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config.database import db_manager
from models.v2_models import ChunkResult, AnomalyResultV2
from services.chunk_service import chunk_service
from services.explanation_service import explanation_service

class WorkerService:
    def __init__(self):
        self.max_workers = 1  # Limitar a un solo worker para evitar concurrencia
        self.workers = []
        self.current_processing_job = None  # Track del job actual
    
    async def process_chunk(self, chunk_data: Dict[str, Any], job_id: str = None) -> ChunkResult:
        """Procesa un chunk individual con streaming de resultados"""
        start_time = time.time()
        chunk_id = str(chunk_data["_id"])
        
        print(f"Procesando chunk {chunk_id} con {len(chunk_data['data'])} caracteres")
        
        # Extraer características y detectar anomalías
        lines = chunk_data["data"].split('\n')
        anomalies = []
        
        # Procesar en lotes para eficiencia y evitar colapso del LLM
        batch_size = 50  # Procesar de 50 en 50 líneas
        max_anomalies_per_chunk = 100  # Limitar anomalías para evitar colapso del LLM
        total_lines = len([line for line in lines if line.strip()])
        processed_lines = 0
        total_anomalies_processed = 0
        
        for i in range(0, len(lines), batch_size):
            # Verificar límite de anomalías para evitar colapso del LLM
            if total_anomalies_processed >= max_anomalies_per_chunk:
                print(f"Límite de {max_anomalies_per_chunk} anomalías alcanzado para chunk {chunk_id}")
                break
                
            batch = lines[i:i + batch_size]
            batch_anomalies = []
            
            # 1. Detectar anomalías en el batch completo
            anomaly_lines = []
            for line in batch:
                if line.strip():
                    # Detectar anomalías basadas en contenido
                    is_anomaly = False
                    score = 0.0
                    
                    # Verificar palabras clave sospechosas
                    suspicious_keywords = ['error', 'failed', 'unauthorized', 'exception', 'timeout', 'denied', 'critical', 'fatal', 'warning']
                    keyword_count = sum(1 for keyword in suspicious_keywords if keyword in line.lower())
                    
                    if keyword_count > 0:
                        is_anomaly = True
                        score = -0.1 * keyword_count  # Más negativo si hay más palabras sospechosas
                    
                    # Verificar patrones inusuales
                    if not is_anomaly:
                        # Detectar logs con muchas mayúsculas (posible error)
                        if len(re.findall(r'[A-Z]', line)) > len(line) * 0.3:
                            is_anomaly = True
                            score = -0.05
                        
                        # Detectar logs muy largos o muy cortos
                        elif len(line) > 500 or len(line) < 20:
                            is_anomaly = True
                            score = -0.03
                        
                        # Detectar patrones de acceso sospechoso
                        elif any(pattern in line.lower() for pattern in ['/admin', '/login', '/wp-admin', '/.env']):
                            is_anomaly = True
                            score = -0.08
                    
                    if is_anomaly:
                        anomaly_lines.append((line, score))
                    
                    processed_lines += 1
            
            # 2. Procesar anomalías en lotes con LLM (solo si hay anomalías)
            if anomaly_lines:
                # Limitar anomalías del batch para evitar colapso
                remaining_anomalies = max_anomalies_per_chunk - total_anomalies_processed
                if len(anomaly_lines) > remaining_anomalies:
                    anomaly_lines = anomaly_lines[:remaining_anomalies]
                    print(f"Limitando anomalías del batch a {remaining_anomalies} para evitar colapso del LLM")
                
                print(f"Procesando {len(anomaly_lines)} anomalías con LLM para chunk {chunk_id}")
                # Procesar anomalías con LLM en lotes
                llm_batch_size = 5  # Procesar 5 anomalías por llamada al LLM
                
                for j in range(0, len(anomaly_lines), llm_batch_size):
                    llm_batch = anomaly_lines[j:j + llm_batch_size]
                    print(f"Procesando lote {j//llm_batch_size + 1} de {len(llm_batch)} anomalías")
                    
                    # Obtener explicaciones para todo el lote de una vez
                    explanations = await explanation_service.get_batch_explanations(llm_batch)
                    print(f"Explicaciones obtenidas: {len(explanations)}")
                    
                    # Crear resultados para cada anomalía
                    for (line, score), explanation in zip(llm_batch, explanations):
                        anomaly_result = AnomalyResultV2(
                            log_entry=line,
                            score=score,
                            is_anomaly=True,
                            explanation=explanation,
                            chunk_id=chunk_id
                        )
                        batch_anomalies.append(anomaly_result)
                        anomalies.append(anomaly_result)
                    
                    print(f"Lote procesado, total anomalías: {len(anomalies)}")
                
                total_anomalies_processed += len(anomaly_lines)
            else:
                print(f"No hay anomalías para procesar en chunk {chunk_id}")
            
            # 3. Guardar batch inmediatamente para evitar pérdida de datos
            if batch_anomalies:
                print(f"Guardando {len(batch_anomalies)} anomalías del batch en MongoDB")
                batch_result = ChunkResult(
                    chunk_id=chunk_id,
                    anomalies=batch_anomalies,
                    processing_time=time.time() - start_time
                )
                await db_manager.mongodb_client.logsanomaly.results.insert_one(batch_result.dict())
                print(f"✅ Batch guardado en MongoDB: {len(batch_anomalies)} anomalías")
            
            # 4. Publicar progreso del batch si hay job_id (para streaming en UI)
            if job_id and batch_anomalies:
                await self._publish_batch_progress(job_id, chunk_id, batch_anomalies, processed_lines, total_lines)
            
            # Pequeña pausa para permitir streaming
            await asyncio.sleep(0.1)
        
        processing_time = time.time() - start_time
        
        print(f"Chunk {chunk_id} procesado: {len(anomalies)} anomalías encontradas en {processing_time:.2f}s")
        print(f"Total anomalías procesadas: {total_anomalies_processed} (límite: {max_anomalies_per_chunk})")
        
        # Crear resultado final (ya se guardó por batches)
        result = ChunkResult(
            chunk_id=chunk_id,
            anomalies=anomalies,
            processing_time=processing_time
        )
        
        # Marcar chunk como procesado
        await chunk_service.mark_chunk_processed(chunk_id, len(anomalies), processing_time)
        
        return result
    
    async def process_file_async(self, file_id: str):
        """Procesa todos los chunks de un archivo de forma secuencial (un archivo a la vez)"""
        # Verificar si ya hay un job procesándose
        if self.current_processing_job and self.current_processing_job != file_id:
            print(f"Ya hay un archivo procesándose: {self.current_processing_job}. Esperando...")
            return []
        
        # Marcar este job como el actual
        self.current_processing_job = file_id
        
        try:
            chunks = await chunk_service.get_chunks_to_process(file_id)
            
            if not chunks:
                print(f"No hay chunks para procesar para el archivo {file_id}")
                return []
            
            print(f"Procesando {len(chunks)} chunks para el archivo {file_id}")
            
            results = []
            
            # Procesar chunks secuencialmente para evitar sobrecarga del LLM
            for i, chunk in enumerate(chunks):
                print(f"Procesando chunk {i+1}/{len(chunks)} del archivo {file_id}")
                result = await self.process_chunk(chunk, file_id)
                results.append(result)
                
                # Publicar progreso del chunk
                await self._publish_chunk_progress(file_id, i+1, len(chunks))
            
            # Actualizar estado del job a completado
            await self._update_job_status(file_id, "completed")
            
            # Publicar evento de completado
            await self._publish_job_completed(file_id)
            
            return results
            
        finally:
            # Limpiar el job actual
            self.current_processing_job = None
    
    async def _publish_batch_progress(self, job_id: str, chunk_id: str, batch_anomalies: List, processed_lines: int, total_lines: int):
        """Publica progreso de un batch de anomalías"""
        try:
            progress_data = {
                "type": "batch_progress",
                "job_id": job_id,
                "chunk_id": chunk_id,
                "anomalies": [anomaly.dict() for anomaly in batch_anomalies],
                "progress": (processed_lines / total_lines) * 100,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publicar a Redis para streaming
            await db_manager.redis_client.publish(
                f"stream:job:{job_id}",
                json.dumps(progress_data)
            )
            
        except Exception as e:
            print(f"Error publicando progreso del batch: {e}")
    
    async def _publish_chunk_progress(self, job_id: str, current_chunk: int, total_chunks: int):
        """Publica progreso de procesamiento de chunks"""
        try:
            progress_data = {
                "type": "chunk_progress",
                "job_id": job_id,
                "current_chunk": current_chunk,
                "total_chunks": total_chunks,
                "progress": (current_chunk / total_chunks) * 100,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publicar a Redis para streaming
            await db_manager.redis_client.publish(
                f"stream:job:{job_id}",
                json.dumps(progress_data)
            )
            
        except Exception as e:
            print(f"Error publicando progreso del chunk: {e}")
    
    async def _publish_job_completed(self, job_id: str):
        """Publica evento de job completado"""
        try:
            completion_data = {
                "type": "job_completed",
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publicar a Redis para streaming
            await db_manager.redis_client.publish(
                f"stream:job:{job_id}",
                json.dumps(completion_data)
            )
            
        except Exception as e:
            print(f"Error publicando completado del job: {e}")
    
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
