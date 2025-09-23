import os
import uuid
import sys
from typing import List, Dict, Any
from datetime import datetime

# Agregar el directorio padre al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config.database import db_manager
from models.v2_models import ChunkData, ProcessingJob, ProcessingStats

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
                    size=len(current_chunk),
                    processed=False
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
                size=len(current_chunk),
                processed=False
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
        from bson import ObjectId
        
        # Actualizar MongoDB
        await db_manager.mongodb_client.logsanomaly.chunks.update_one(
            {"_id": ObjectId(chunk_id)},
            {"$set": {"processed": True}}
        )
        
        # Obtener información del chunk para las estadísticas
        chunk = await db_manager.mongodb_client.logsanomaly.chunks.find_one({"_id": ObjectId(chunk_id)})
        
        if chunk:
            # Guardar estadísticas en PostgreSQL
            stats = ProcessingStats(
                id=str(uuid.uuid4()),
                job_id=chunk["file_id"],
                chunk_number=chunk["chunk_number"],
                processing_time=processing_time,
                anomalies_found=anomalies_count
            )
            
            async with db_manager.postgres_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO processing_stats (id, job_id, chunk_number, processing_time, anomalies_found)
                    VALUES ($1, $2, $3, $4, $5)
                """, stats.id, stats.job_id, stats.chunk_number, stats.processing_time, stats.anomalies_found)

chunk_service = ChunkService()
