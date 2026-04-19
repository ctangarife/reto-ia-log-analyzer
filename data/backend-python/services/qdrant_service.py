"""
Servicio de Qdrant para búsqueda de similitud de logs
Permite encontrar logs normales similares a anomalías para comparación educativa
"""
import os
import uuid
import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from .embedding_service import VECTOR_SIZE, generate_embeddings

logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NORMAL_LOGS = os.getenv("QDRANT_COLLECTION_NORMAL_LOGS", "normal_logs")
COLLECTION_ANOMALIES = os.getenv("QDRANT_COLLECTION_ANOMALIES", "anomalies")

# Cliente Qdrant global
client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """
    Obtiene o crea el cliente de Qdrant.
    """
    global client
    if client is None:
        try:
            client = QdrantClient(url=QDRANT_URL)
            logger.info(f"Cliente Qdrant conectado: {QDRANT_URL}")
        except Exception as e:
            logger.error(f"Error al conectar con Qdrant: {e}")
            raise
    return client


async def ensure_collection(collection_name: str):
    """
    Asegura que la colección existe en Qdrant con el tamaño correcto.
    
    Args:
        collection_name: Nombre de la colección a crear/verificar
    """
    qdrant = get_qdrant_client()
    
    try:
        # Verificar si la colección existe
        collections = qdrant.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if collection_name not in collection_names:
            # Crear la colección si no existe
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Colección '{collection_name}' creada en Qdrant con tamaño {VECTOR_SIZE}")
        else:
            logger.debug(f"Colección '{collection_name}' ya existe en Qdrant")
            
    except Exception as e:
        logger.error(f"Error al asegurar colección en Qdrant: {e}", exc_info=True)
        raise


async def store_normal_logs(
    job_id: str,
    log_entries: List[str],
    metadata: Optional[List[Dict]] = None
) -> List[str]:
    """
    Almacena logs normales en Qdrant para comparación posterior.
    
    Args:
        job_id: ID del job de procesamiento
        log_entries: Lista de textos de logs normales
        metadata: Lista opcional de metadatos para cada log
    
    Returns:
        Lista de IDs de puntos creados en Qdrant
    """
    qdrant = get_qdrant_client()
    
    # Asegurar que la colección existe
    await ensure_collection(COLLECTION_NORMAL_LOGS)
    
    if not log_entries:
        logger.warning(f"No hay logs normales para almacenar para job {job_id}")
        return []
    
    try:
        # Generar embeddings para los logs
        logger.info(f"Generando embeddings para {len(log_entries)} logs normales...")
        embeddings = generate_embeddings(log_entries)
        
        if len(embeddings) != len(log_entries):
            raise ValueError(f"El número de embeddings ({len(embeddings)}) no coincide con el número de logs ({len(log_entries)})")
        
        # Crear puntos para Qdrant
        points = []
        point_ids = []
        
        for i, (log_entry, embedding) in enumerate(zip(log_entries, embeddings)):
            # Validar tamaño del embedding
            if len(embedding) != VECTOR_SIZE:
                raise ValueError(f"Embedding {i} tiene tamaño incorrecto: {len(embedding)} (esperado: {VECTOR_SIZE})")
            
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            # Metadatos del log
            payload = {
                "job_id": job_id,
                "log_entry": log_entry,
                "log_index": i,
            }
            
            # Agregar metadatos adicionales si están disponibles
            if metadata and i < len(metadata):
                payload.update(metadata[i])
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            points.append(point)
        
        # Insertar puntos en lotes de 100 para evitar problemas con lotes grandes
        BATCH_SIZE = 100
        stored_count = 0
        
        for batch_start in range(0, len(points), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(points))
            batch_points = points[batch_start:batch_end]
            
            qdrant.upsert(
                collection_name=COLLECTION_NORMAL_LOGS,
                points=batch_points
            )
            
            stored_count += len(batch_points)
            logger.debug(f"Almacenados {stored_count}/{len(points)} logs normales")
        
        logger.info(f"✅ Almacenados {stored_count} logs normales en Qdrant para job {job_id}")
        return point_ids
        
    except Exception as e:
        logger.error(f"Error al almacenar logs normales en Qdrant: {e}", exc_info=True)
        raise


async def store_anomaly(
    anomaly_id: str,
    log_entry: str,
    anomaly_score: float,
    metadata: Optional[Dict] = None
) -> str:
    """
    Almacena una anomalía en Qdrant para agrupación y correlación.
    
    Args:
        anomaly_id: ID único de la anomalía
        log_entry: Texto del log anómalo
        anomaly_score: Score de anomalía
        metadata: Metadatos adicionales (job_id, timestamp, etc.)
    
    Returns:
        ID del punto creado en Qdrant
    """
    qdrant = get_qdrant_client()
    
    # Asegurar que la colección existe
    await ensure_collection(COLLECTION_ANOMALIES)
    
    try:
        # Generar embedding para la anomalía
        embedding = generate_embeddings([log_entry])[0]
        
        if len(embedding) != VECTOR_SIZE:
            raise ValueError(f"Embedding tiene tamaño incorrecto: {len(embedding)} (esperado: {VECTOR_SIZE})")
        
        # Payload con información de la anomalía
        payload = {
            "anomaly_id": anomaly_id,
            "log_entry": log_entry,
            "anomaly_score": float(anomaly_score),
        }
        
        # Agregar metadatos adicionales
        if metadata:
            payload.update(metadata)
        
        point = PointStruct(
            id=anomaly_id,
            vector=embedding,
            payload=payload
        )
        
        qdrant.upsert(
            collection_name=COLLECTION_ANOMALIES,
            points=[point]
        )
        
        logger.debug(f"Anomalía {anomaly_id} almacenada en Qdrant")
        return anomaly_id
        
    except Exception as e:
        logger.error(f"Error al almacenar anomalía en Qdrant: {e}", exc_info=True)
        raise


async def find_similar_normal_logs(
    log_entry: str,
    limit: int = 5,
    min_score: float = 0.3,
    job_id: Optional[str] = None
) -> List[Dict]:
    """
    Encuentra logs normales similares a un log dado.
    Útil para comparación educativa: mostrar qué es normal vs anómalo.
    
    Args:
        log_entry: Texto del log a comparar
        limit: Número máximo de resultados
        min_score: Score mínimo de similitud (0-1)
        job_id: Filtrar por job_id específico (opcional)
    
    Returns:
        Lista de logs normales similares con sus scores de similitud
    """
    qdrant = get_qdrant_client()
    
    try:
        # Generar embedding para el log de consulta
        query_embedding = generate_embeddings([log_entry])[0]
        
        if len(query_embedding) != VECTOR_SIZE:
            raise ValueError(f"Embedding de consulta tiene tamaño incorrecto: {len(query_embedding)} (esperado: {VECTOR_SIZE})")
        
        # Construir filtro si se especifica job_id
        query_filter = None
        if job_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="job_id",
                        match=MatchValue(value=job_id)
                    )
                ]
            )
        
        # Buscar logs similares
        results = qdrant.search(
            collection_name=COLLECTION_NORMAL_LOGS,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            score_threshold=min_score
        )
        
        # Formatear resultados
        similar_logs = []
        for result in results:
            similar_logs.append({
                "log_entry": result.payload.get("log_entry", ""),
                "similarity_score": float(result.score),
                "job_id": result.payload.get("job_id", ""),
                "log_index": result.payload.get("log_index", 0),
                "metadata": {k: v for k, v in result.payload.items() 
                           if k not in ["log_entry", "job_id", "log_index"]}
            })
        
        logger.info(f"Encontrados {len(similar_logs)} logs normales similares (score mínimo: {min_score})")
        return similar_logs
        
    except Exception as e:
        logger.error(f"Error al buscar logs similares en Qdrant: {e}", exc_info=True)
        raise


async def find_similar_anomalies(
    anomaly_id: str,
    limit: int = 10,
    min_score: float = 0.5
) -> List[Dict]:
    """
    Encuentra anomalías similares a una anomalía dada.
    Útil para agrupación y detección de patrones.
    
    Args:
        anomaly_id: ID de la anomalía de referencia
        limit: Número máximo de resultados
        min_score: Score mínimo de similitud (0-1)
    
    Returns:
        Lista de anomalías similares con sus scores
    """
    qdrant = get_qdrant_client()
    
    try:
        # Obtener el vector de la anomalía de referencia
        point = qdrant.retrieve(
            collection_name=COLLECTION_ANOMALIES,
            ids=[anomaly_id],
            with_vectors=True
        )
        
        if not point:
            logger.warning(f"Anomalía {anomaly_id} no encontrada en Qdrant")
            return []
        
        query_vector = point[0].vector
        
        # Buscar anomalías similares (excluyendo la misma anomalía)
        results = qdrant.search(
            collection_name=COLLECTION_ANOMALIES,
            query_vector=query_vector,
            query_filter=Filter(
                must_not=[
                    FieldCondition(
                        key="anomaly_id",
                        match=MatchValue(value=anomaly_id)
                    )
                ]
            ),
            limit=limit + 1,  # +1 porque excluimos la misma anomalía
            score_threshold=min_score
        )
        
        # Formatear resultados
        similar_anomalies = []
        for result in results:
            # Excluir la misma anomalía
            if result.payload.get("anomaly_id") == anomaly_id:
                continue
            
            similar_anomalies.append({
                "anomaly_id": result.payload.get("anomaly_id", ""),
                "log_entry": result.payload.get("log_entry", ""),
                "anomaly_score": result.payload.get("anomaly_score", 0.0),
                "similarity_score": float(result.score),
                "metadata": {k: v for k, v in result.payload.items() 
                           if k not in ["anomaly_id", "log_entry", "anomaly_score"]}
            })
        
        logger.info(f"Encontradas {len(similar_anomalies)} anomalías similares a {anomaly_id}")
        return similar_anomalies[:limit]  # Limitar al número solicitado
        
    except Exception as e:
        logger.error(f"Error al buscar anomalías similares en Qdrant: {e}", exc_info=True)
        raise


async def delete_job_logs(job_id: str):
    """
    Elimina todos los logs normales asociados a un job.
    
    Args:
        job_id: ID del job
    """
    qdrant = get_qdrant_client()
    
    try:
        qdrant.delete(
            collection_name=COLLECTION_NORMAL_LOGS,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="job_id",
                        match=MatchValue(value=job_id)
                    )
                ]
            )
        )
        logger.info(f"Logs normales eliminados para job {job_id}")
        
    except Exception as e:
        logger.error(f"Error al eliminar logs normales de Qdrant: {e}")
        raise

