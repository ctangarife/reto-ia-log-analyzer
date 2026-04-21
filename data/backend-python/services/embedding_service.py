"""
Servicio de generación de embeddings para logs
Usa FastEmbed para convertir logs en vectores para búsqueda de similitud
FastEmbed es una alternativa ligera (~50MB) a sentence-transformers (~2GB)
"""
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

# Modelo global para evitar cargarlo múltiples veces
_model = None

# Tamaño del vector (384 para bge-small-en-v1.5)
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))

# Modelos disponibles en FastEmbed con sus tamaños (usar nombres completos con prefijo)
AVAILABLE_MODELS = {
    "BAAI/bge-small-en": 384,   # Ligero, rápido, 384 dimensiones
    "BAAI/bge-small-en-v1.5": 384,   # v1.5 mejorado, 384 dimensiones
    "BAAI/bge-base-en": 768,    # Base, más preciso, 768 dimensiones
    "BAAI/bge-base-en-v1.5": 768,    # v1.5 mejorado, 768 dimensiones
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,  # Multilingüe
    "snowflake/snowflake-arctic-embed-xs": 384,  # Muy ligero, 384 dimensiones
}

# Modelo por defecto (nombre completo con prefijo)
DEFAULT_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-base-en-v1.5")


def get_vector_size_for_model(model_name: str) -> int:
    """Obtiene el tamaño de vector para un modelo específico."""
    return AVAILABLE_MODELS.get(model_name, 384)


def get_embedding_model():
    """
    Obtiene o carga el modelo de embeddings.
    Usa FastEmbed con un modelo ligero optimizado para logs.
    """
    global _model

    if _model is None:
        try:
            model_name = DEFAULT_MODEL
            expected_size = get_vector_size_for_model(model_name)

            logger.info(f"Cargando modelo de embeddings FastEmbed: {model_name}")

            # API actualizada de FastEmbed (v0.3.0+)
            from fastembed import TextEmbedding

            # Inicializar modelo de FastEmbed
            _model = TextEmbedding(
                model_name=model_name,
                cache_dir="/tmp/fastembed_cache"  # Cache en temp para no persistir en container
            )

            # Verificar tamaño del vector
            if expected_size != VECTOR_SIZE:
                logger.warning(
                    f"El modelo '{model_name}' genera vectores de tamaño {expected_size} "
                    f"pero QDRANT_VECTOR_SIZE está configurado como {VECTOR_SIZE}. "
                    f"Usando {expected_size} como tamaño de vector."
                )

            logger.info(f"Modelo FastEmbed cargado: {model_name} (tamaño de vector: {expected_size})")

        except Exception as e:
            logger.error(f"Error al cargar modelo de embeddings FastEmbed: {e}")
            _model = None
            raise

    return _model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos (logs).

    Args:
        texts: Lista de textos de logs a convertir en embeddings

    Returns:
        Lista de vectores de embeddings (dimensiones según el modelo)
    """
    if not texts:
        return []

    try:
        model = get_embedding_model()

        # Filtrar textos vacíos y reemplazar con espacio
        valid_texts = [text if text and text.strip() else " " for text in texts]

        # Generar embeddings usando FastEmbed
        # FastEmbed devuelve un generador, lo convertimos a lista
        embeddings = list(model.embed(valid_texts))

        # Convertir a lista de listas si no lo está ya
        embeddings_list = [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]

        # Validar que se generaron los embeddings correctamente
        if len(embeddings_list) != len(valid_texts):
            logger.error(f"No se generaron todos los embeddings: {len(embeddings_list)}/{len(valid_texts)}")
            raise ValueError(f"No se pudieron generar todos los embeddings")

        # Validar tamaño de embeddings (solo el primero para no ser demasiado lento)
        if embeddings_list:
            first_size = len(embeddings_list[0])
            if first_size != VECTOR_SIZE:
                logger.warning(
                    f"Los embeddings tienen tamaño {first_size} "
                    f"(esperado: {VECTOR_SIZE}). Esto puede causar problemas con Qdrant."
                )

        logger.debug(f"Generados {len(embeddings_list)} embeddings de tamaño {len(embeddings_list[0]) if embeddings_list else 0}")
        return embeddings_list

    except Exception as e:
        logger.error(f"Error al generar embeddings: {e}", exc_info=True)
        raise


def preload_model():
    """
    Precarga el modelo de embeddings al iniciar la aplicación.
    Llamar esto durante el startup de la aplicación para evitar latencia en la primera petición.
    """
    try:
        logger.info("Precargando modelo de embeddings...")
        get_embedding_model()
        logger.info("Modelo de embeddings precargado exitosamente")
    except Exception as e:
        logger.error(f"Error al precargar modelo de embeddings: {e}")
