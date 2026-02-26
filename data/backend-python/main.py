"""
Anomaly Detector Service - Versión Consolidada
Arquitectura refactorizada con SOLID y Ollama Cloud
"""
import os
import sys
import logging
import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Agregar el directorio actual al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Imports de configuración y modelos
from config.database import db_manager
from models.v2_models import (
    ProcessResponseV2, StatusResponseV2, ProcessingStatus
)
from services.chunk_service import chunk_service
from services.worker_service import worker_service
from services.monitoring_service import monitoring_service

# Imports de rutas
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.workspaces import router as workspaces_router
from routes.projects import router as projects_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("anomaly_detector")

# Inicializar FastAPI
app = FastAPI(
    title="Anomaly Detector Service",
    description="Servicio para detectar anomalías en logs usando Isolation Forest y explicaciones con LLM",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class HealthResponse:
    status: str

# === INICIALIZACIÓN DE BASES DE DATOS ===
@app.on_event("startup")
async def startup_event():
    """Inicializar conexiones a bases de datos"""
    try:
        await db_manager.connect_all()
        logger.info("✅ Todas las bases de datos conectadas")
        
        # Inicializar servicio de monitoreo
        monitoring_service.set_services(db_manager, worker_service)
        asyncio.create_task(monitoring_service.start_monitoring(interval=30))
        logger.info("✅ Servicio de monitoreo iniciado")
        
    except Exception as e:
        logger.error(f"❌ Error conectando bases de datos: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar conexiones a bases de datos"""
    # Detener servicio de monitoreo
    monitoring_service.stop_monitoring()
    
    if db_manager.mongodb_client:
        db_manager.mongodb_client.close()
    if db_manager.postgres_pool:
        await db_manager.postgres_pool.close()
    if db_manager.redis_client:
        await db_manager.redis_client.close()

# === REGISTRAR RUTAS ===
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(workspaces_router)
app.include_router(projects_router)

# === ENDPOINTS ===

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/process", response_model=ProcessResponseV2)
async def process_file(file: UploadFile = File(...)):
    """
    Procesar archivo usando arquitectura multi-DB con servicios refactorizados.
    Usa ExplanationService con Ollama Cloud para generar explicaciones.
    """
    try:
        # Verificar si ya hay un archivo procesándose
        if worker_service.current_processing_job:
            raise HTTPException(
                status_code=409, 
                detail=f"Ya hay un archivo procesándose: {worker_service.current_processing_job}. Solo se puede procesar un archivo a la vez."
            )
        
        # Leer contenido del archivo
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Crear chunks y job
        file_id = await chunk_service.create_chunks_from_file(file_content, file.filename)
        logger.info(f"✅ Chunks creados para archivo {file.filename}, file_id: {file_id}")
        
        # Iniciar procesamiento asíncrono
        logger.info(f"🚀 Iniciando procesamiento asíncrono para {file_id}")
        task = asyncio.create_task(worker_service.process_file_async(file_id))
        logger.info(f"📋 Tarea de procesamiento creada: {task}")
        
        # Actualizar estado a processing
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                UPDATE processing.processing_jobs 
                SET status = $1, started_at = $2 
                WHERE id = $3
            """, ProcessingStatus.PROCESSING, datetime.utcnow(), file_id)
        logger.info(f"📊 Estado actualizado a processing para {file_id}")
        
        return ProcessResponseV2(
            job_id=file_id,
            status=ProcessingStatus.PROCESSING,
            message="Procesamiento iniciado",
            total_chunks=len(file_content.split('\n')) // 1000  # Estimación
        )
        
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}", response_model=StatusResponseV2)
async def get_status(job_id: str):
    """Obtener estado de procesamiento"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            job = await conn.fetchrow("""
                SELECT * FROM processing.processing_jobs WHERE id = $1
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

@app.get("/results/{job_id}/stream")
async def stream_results(job_id: str):
    """Stream de resultados en tiempo real usando Redis Pub/Sub"""
    async def generate():
        try:
            # Suscribirse al canal de Redis para este job
            pubsub = db_manager.redis_client.pubsub()
            await pubsub.subscribe(f"stream:job:{job_id}")
            
            logger.info(f"Iniciando stream para job {job_id}")
            
            # Enviar evento inicial
            yield f"data: {{'type': 'stream_started', 'job_id': '{job_id}'}}\n\n"
            
            # Escuchar eventos del stream
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield f"data: {json.dumps(data)}\n\n"
                        
                        # Si el job está completado, terminar el stream
                        if data.get('type') == 'job_completed':
                            logger.info(f"Job {job_id} completado, terminando stream")
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decodificando mensaje: {e}")
                        continue
            
            # Desuscribirse
            await pubsub.unsubscribe(f"stream:job:{job_id}")
            await pubsub.close()
            
        except Exception as e:
            logger.error(f"Error en stream: {e}")
            yield f"data: {{'type': 'error', 'message': '{str(e)}'}}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancelar procesamiento"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                UPDATE processing.processing_jobs 
                SET status = $1, completed_at = $2 
                WHERE id = $3
            """, ProcessingStatus.CANCELLED, datetime.utcnow(), job_id)
        
        return {"message": "Procesamiento cancelado", "job_id": job_id}
        
    except Exception as e:
        logger.error(f"Error cancelando job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports")
async def get_reports():
    """Obtener todos los reportes desde la base de datos"""
    try:
        # Obtener todos los jobs completados
        async with db_manager.postgres_pool.acquire() as conn:
            jobs = await conn.fetch("""
                SELECT * FROM processing.processing_jobs 
                WHERE status = 'completed' 
                ORDER BY completed_at DESC
            """)
        
        reports = []
        
        for job in jobs:
            job_id = job["id"]
            
            # Obtener chunks del job (convertir UUID a string para MongoDB)
            chunks = await db_manager.mongodb_client.logsanomaly.chunks.find({
                "file_id": str(job_id)
            }).to_list(length=None)
            
            # Obtener resultados de anomalías usando los chunk_ids
            chunk_ids = [str(chunk["_id"]) for chunk in chunks]
            results = await db_manager.mongodb_client.logsanomaly.results.find({
                "chunk_id": {"$in": chunk_ids}
            }).to_list(length=None)
            
            # Agregar anomalías de todos los chunks
            all_anomalies = []
            for result in results:
                if "anomalies" in result:
                    all_anomalies.extend(result["anomalies"])
            
            # Calcular estadísticas
            total_logs = sum(len(chunk["data"].split('\n')) for chunk in chunks)
            anomalies_detected = len(all_anomalies)
            chunks_processed = len([chunk for chunk in chunks if chunk.get("processed", False)])
            
            # Crear reporte
            report = {
                "id": str(job_id),
                "timestamp": job["completed_at"].isoformat() if job["completed_at"] else job["started_at"].isoformat(),
                "fileName": job["filename"],
                "total_logs": total_logs,
                "anomalies_detected": anomalies_detected,
                "anomalies": all_anomalies,
                "report_file": f"db_report_{job_id}.json",
                "file_id": str(job_id),
                "status": job["status"],
                "total_chunks": job["total_chunks"],
                "chunks_processed": chunks_processed
            }
            
            reports.append(report)
        
        logger.info(f"Retornando {len(reports)} reportes desde la base de datos")
        return reports
        
    except Exception as e:
        logger.error(f"Error obteniendo reportes desde BD: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === ENDPOINTS DE MONITOREO ===

@app.get("/monitoring/status")
async def get_system_status():
    """Obtener estado actual del sistema"""
    try:
        summary = monitoring_service.get_system_summary()
        return summary
    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/history")
async def get_memory_history(limit: int = 100):
    """Obtener historial de memoria"""
    try:
        history = monitoring_service.get_memory_history(limit)
        return {"history": history}
    except Exception as e:
        logger.error(f"Error obteniendo historial de memoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/alerts")
async def get_system_alerts(limit: int = 50):
    """Obtener alertas del sistema"""
    try:
        alerts = monitoring_service.get_recent_alerts(limit)
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """Obtener datos completos para dashboard de monitoreo"""
    try:
        current_stats = monitoring_service.get_current_stats()
        history = monitoring_service.get_memory_history(100)
        alerts = monitoring_service.get_recent_alerts(50)
        summary = monitoring_service.get_system_summary()
        
        return {
            "current_stats": current_stats.__dict__ if current_stats else None,
            "history": history,
            "alerts": alerts,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo dashboard de monitoreo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
