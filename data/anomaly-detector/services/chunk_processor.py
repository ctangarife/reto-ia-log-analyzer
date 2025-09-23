import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis
import asyncio
from math import ceil

class ChunkProcessor:
    def __init__(
        self,
        mongodb_client: AsyncIOMotorClient,
        postgres_session: AsyncSession,
        redis_client: aioredis.Redis,
        chunk_size: int = 1024 * 1024  # 1MB por defecto
    ):
        self.mongodb = mongodb_client
        self.postgres = postgres_session
        self.redis = redis_client
        self.chunk_size = chunk_size

    async def process_large_file(
        self,
        file_path: str,
        filename: str
    ) -> Dict[str, Any]:
        """Procesa un archivo grande dividiéndolo en chunks"""
        try:
            # 1. Crear registro de procesamiento en PostgreSQL
            file_size = os.path.getsize(file_path)
            total_chunks = ceil(file_size / self.chunk_size)
            
            processing_job = await self._create_processing_job(
                filename=filename,
                total_size=file_size,
                total_chunks=total_chunks
            )
            
            # 2. Dividir y almacenar chunks en MongoDB
            chunks_info = await self._split_and_store_chunks(
                file_path=file_path,
                job_id=processing_job["id"]
            )
            
            # 3. Encolar chunks para procesamiento
            await self._enqueue_chunks_for_processing(chunks_info)
            
            return {
                "job_id": processing_job["id"],
                "filename": filename,
                "total_size": file_size,
                "total_chunks": total_chunks,
                "status": "processing"
            }
            
        except Exception as e:
            # En caso de error, actualizar estado del job
            if processing_job:
                await self._update_job_status(
                    job_id=processing_job["id"],
                    status="failed",
                    error_message=str(e)
                )
            raise e

    async def _create_processing_job(
        self,
        filename: str,
        total_size: int,
        total_chunks: int
    ) -> Dict[str, Any]:
        """Crea un nuevo job de procesamiento en PostgreSQL"""
        job_id = str(uuid.uuid4())
        query = """
        INSERT INTO processing_jobs 
        (id, filename, total_size, total_chunks, status)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, filename, total_size, total_chunks, status
        """
        result = await self.postgres.execute(
            query,
            job_id,
            filename,
            total_size,
            total_chunks,
            "pending"
        )
        await self.postgres.commit()
        return dict(result.first())

    async def _split_and_store_chunks(
        self,
        file_path: str,
        job_id: str
    ) -> List[Dict[str, Any]]:
        """Divide el archivo en chunks y los almacena en MongoDB"""
        chunks_info = []
        chunk_number = 0
        
        with open(file_path, 'r') as file:
            while True:
                chunk_data = file.read(self.chunk_size)
                if not chunk_data:
                    break
                
                # Asegurar que no cortamos en medio de una línea
                if chunk_data[-1] != '\n':
                    next_char = file.read(1)
                    while next_char and next_char != '\n':
                        chunk_data += next_char
                        next_char = file.read(1)
                    if next_char == '\n':
                        chunk_data += next_char
                
                # Almacenar chunk en MongoDB
                chunk_id = str(uuid.uuid4())
                chunk_info = {
                    "id": chunk_id,
                    "job_id": job_id,
                    "chunk_number": chunk_number,
                    "data": chunk_data,
                    "size": len(chunk_data),
                    "processed": False,
                    "created_at": datetime.utcnow()
                }
                
                await self.mongodb.chunks.insert_one(chunk_info)
                chunks_info.append(chunk_info)
                chunk_number += 1
        
        return chunks_info

    async def _enqueue_chunks_for_processing(
        self,
        chunks_info: List[Dict[str, Any]]
    ) -> None:
        """Encola los chunks para procesamiento en Redis"""
        # Crear lista de chunks pendientes
        pipeline = self.redis.pipeline()
        for chunk in chunks_info:
            # Agregar a la cola de procesamiento
            pipeline.lpush(
                "queue:chunks_to_process",
                json.dumps({
                    "chunk_id": chunk["id"],
                    "job_id": chunk["job_id"],
                    "chunk_number": chunk["chunk_number"]
                })
            )
            
            # Establecer estado inicial en Redis
            pipeline.hset(
                f"processing:chunk:{chunk['id']}",
                mapping={
                    "status": "pending",
                    "progress": "0",
                    "start_time": "",
                    "end_time": "",
                    "error": ""
                }
            )
        
        await pipeline.execute()

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Actualiza el estado de un job en PostgreSQL"""
        query = """
        UPDATE processing_jobs
        SET status = $1, error_message = $2, updated_at = NOW()
        WHERE id = $3
        """
        await self.postgres.execute(
            query,
            status,
            error_message,
            job_id
        )
        await self.postgres.commit()

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Obtiene el estado actual de un job"""
        # Obtener información básica del job
        query = """
        SELECT id, filename, total_size, total_chunks, chunks_processed,
               status, error_message, started_at, completed_at
        FROM processing_jobs
        WHERE id = $1
        """
        result = await self.postgres.execute(query, job_id)
        job_info = dict(result.first())
        
        # Obtener progreso de chunks desde Redis
        chunks_status = []
        for i in range(job_info["total_chunks"]):
            chunk_status = await self.redis.hgetall(
                f"processing:chunk:{job_id}_{i}"
            )
            if chunk_status:
                chunks_status.append(chunk_status)
        
        # Calcular progreso total
        processed_chunks = len([
            c for c in chunks_status if c.get("status") == "completed"
        ])
        total_progress = (processed_chunks / job_info["total_chunks"]) * 100
        
        return {
            **job_info,
            "chunks_status": chunks_status,
            "total_progress": total_progress
        }
