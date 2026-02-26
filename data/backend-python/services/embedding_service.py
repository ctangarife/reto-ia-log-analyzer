"""
Servicio de generación de embeddings para logs
Usa sentence-transformers para convertir logs en vectores para búsqueda de similitud
"""
import logging
import os
from typing import List
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

# Modelo global para evitar cargarlo múltiples veces
_model: SentenceTransformer = None

# Tamaño del vector (384 para all-MiniLM-L6-v2)
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))


def get_embedding_model() -> SentenceTransformer:
    """
    Obtiene o carga el modelo de embeddings.
    Usa un modelo ligero y rápido optimizado para logs.
    """
    global _model
    
    if _model is None:
        try:
            # Modelo ligero y rápido: all-MiniLM-L6-v2
            # Vector size: 384
            # Buen rendimiento para similitud semántica de texto
            model_name = "all-MiniLM-L6-v2"
            
            logger.info(f"Cargando modelo de embeddings: {model_name}")
            _model = SentenceTransformer(model_name)
            
            # Validar que el modelo genera vectores del tamaño esperado
            model_size = _model.get_sentence_embedding_dimension()
            
            if model_size != VECTOR_SIZE:
                error_msg = (
                    f"ERROR CRÍTICO: El modelo '{model_name}' genera vectores de tamaño {model_size} "
                    f"pero se espera {VECTOR_SIZE}. Esto causará corrupción de datos en Qdrant. "
                    f"Por favor, verifica que el modelo es correcto o ajusta QDRANT_VECTOR_SIZE en .env"
                )
                logger.error(error_msg)
                _model = None
                raise ValueError(error_msg)
            
            logger.info(f"Modelo cargado correctamente: {model_name} (tamaño de vector: {model_size})")
            
            # Usar GPU si está disponible
            if torch.cuda.is_available():
                _model = _model.to('cuda')
                logger.info("Modelo cargado en GPU")
            else:
                logger.info("Modelo cargado en CPU")
                
        except Exception as e:
            logger.error(f"Error al cargar modelo de embeddings: {e}")
            raise
    
    return _model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos (logs).
    
    Args:
        texts: Lista de textos de logs a convertir en embeddings
    
    Returns:
        Lista de vectores de embeddings (384 dimensiones cada uno)
    """
    if not texts:
        return []
    
    try:
        model = get_embedding_model()
        
        # Validar que el tamaño del modelo coincide con el esperado
        model_size = model.get_sentence_embedding_dimension()
        
        if model_size != VECTOR_SIZE:
            error_msg = (
                f"ERROR CRÍTICO: El modelo de embeddings genera vectores de tamaño {model_size} "
                f"pero se espera {VECTOR_SIZE}. Esto causará corrupción de datos en Qdrant."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Filtrar textos vacíos y reemplazar con espacio
        valid_texts = [text if text and text.strip() else " " for text in texts]
        
        # Generar embeddings en batch
        embeddings = model.encode(
            valid_texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
            normalize_embeddings=True  # Normalizar para mejor rendimiento en similitud coseno
        )
        
        # Convertir a lista de listas
        embeddings_list = embeddings.tolist()
        
        # Validar tamaño de embeddings (doble verificación)
        for i, emb in enumerate(embeddings_list):
            if len(emb) != VECTOR_SIZE:
                logger.error(f"Embedding {i} tiene tamaño incorrecto: {len(emb)} (esperado: {VECTOR_SIZE})")
                raise ValueError(f"Embedding generado tiene tamaño incorrecto: {len(emb)} (esperado: {VECTOR_SIZE})")
        
        logger.debug(f"Generados {len(embeddings_list)} embeddings de tamaño {VECTOR_SIZE}")
        return embeddings_list
        
    except Exception as e:
        logger.error(f"Error al generar embeddings: {e}", exc_info=True)
        raise

