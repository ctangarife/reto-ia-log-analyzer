import asyncio
import time
import os
import sys
import re
import json
import uuid
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
from services import qdrant_service
from services.embedding_service import generate_embeddings
from services.format_detector import format_detector, FileFormat

class WorkerService:
    def __init__(self):
        self.max_workers = 1  # Limitar a un solo worker para evitar concurrencia
        self.workers = []
        self.current_processing_job = None  # Track del job actual

        # Configuración de detección con embeddings
        self.similarity_threshold = float(os.getenv("ANOMALY_SIMILARITY_THRESHOLD", "0.4"))  # Logs con < 0.4 similitud son anomalías
        self.store_normal_logs = os.getenv("STORE_NORMAL_LOGS", "true").lower() == "true"
        self.embedding_sample_rate = int(os.getenv("EMBEDDING_SAMPLE_RATE", "10"))  # 1 de cada N líneas usa embeddings
        self._line_counter = 0  # Contador para muestreo

    def _has_sufficient_global_normal_logs(self) -> bool:
        """
        Verifica si hay suficientes logs normales globales para búsqueda global.

        Returns:
            True si hay ≥100 logs normales acumulados globalmente
        """
        try:
            qdrant = qdrant_service.get_qdrant_client()
            collection_info = qdrant.get_collection(qdrant_service.COLLECTION_NORMAL_LOGS)
            total_points = collection_info.points_count
            return total_points >= 100
        except Exception as e:
            # Silenciar errores de validación de Pydantic (no críticos)
            if "validation errors" not in str(e):
                logger.warning(f"Error verificando logs globales: {e}")
            return False

    async def _detect_anomaly_with_embeddings(
        self,
        log_line: str,
        job_id: str
    ) -> tuple[bool, float, list, str]:
        """
        Detecta anomalías usando búsqueda de similitud vectorial en Qdrant.
        Sistema híbrido de tres niveles:

        1. qdrant_global: Búsqueda global cuando hay ≥100 logs normales acumulados
        2. qdrant_job: Búsqueda específica del job cuando hay suficientes datos del job
        3. isolation_forest: Fallback cuando no hay suficientes datos

        Args:
            log_line: Línea de log a analizar
            job_id: ID del job actual

        Returns:
            (is_anomaly, similarity_score, similar_logs, detection_method)
        """
        try:
            # MODO 1: Búsqueda global (acumulativa) - requiere ≥100 logs normales globales
            if self._has_sufficient_global_normal_logs():
                similar_logs = await qdrant_service.find_similar_normal_logs(
                    log_entry=log_line,
                    limit=3,
                    min_score=0.0,
                    job_id=job_id,
                    global_search=True  # Buscar en TODOS los jobs acumulados
                )
                detection_method = "qdrant_global"
            else:
                # MODO 2: Búsqueda específica del job
                similar_logs = await qdrant_service.find_similar_normal_logs(
                    log_entry=log_line,
                    limit=3,
                    min_score=0.0,
                    job_id=job_id,
                    global_search=False  # Solo buscar en este job
                )
                detection_method = "qdrant_job"

            if not similar_logs:
                # MODO 3: Fallback - No hay suficientes datos de referencia
                return False, 0.0, [], "isolation_forest_fallback"

            # Calcular score máximo de similitud
            max_similarity = max(log["similarity_score"] for log in similar_logs)

            # Si la similitud máxima está por debajo del threshold, es anomalía
            is_anomaly = max_similarity < self.similarity_threshold

            return is_anomaly, max_similarity, similar_logs, detection_method

        except Exception as e:
            print(f"Error en detección con embeddings: {e}")
            # Fallback a no-anomalía si hay error
            return False, 0.0, [], "error"

    async def _store_normal_logs_batch(
        self,
        normal_logs: list[str],
        job_id: str
    ):
        """
        Almacena un batch de logs normales en Qdrant.

        Args:
            normal_logs: Lista de logs normales
            job_id: ID del job
        """
        if not normal_logs or not self.store_normal_logs:
            return

        try:
            await qdrant_service.store_normal_logs(
                job_id=job_id,
                log_entries=normal_logs
            )
            print(f"✅ {len(normal_logs)} logs normales almacenados en Qdrant")

        except Exception as e:
            print(f"⚠️  Error almacenando logs normales: {e}")

    async def _store_anomaly_in_qdrant(
        self,
        log_line: str,
        anomaly_score: float,
        anomaly_id: str,
        job_id: str
    ):
        """
        Almacena una anomalía en Qdrant para correlación futura.

        Args:
            log_line: Log anómalo
            anomaly_score: Score de anomalía
            anomaly_id: ID único
            job_id: ID del job
        """
        try:
            await qdrant_service.store_anomaly(
                anomaly_id=anomaly_id,
                log_entry=log_line,
                anomaly_score=anomaly_score,
                metadata={"job_id": job_id}
            )

        except Exception as e:
            print(f"⚠️  Error almacenando anomalía en Qdrant: {e}")

    async def process_chunk(self, chunk_data: Dict[str, Any], job_id: str = None) -> ChunkResult:
        """Procesa un chunk individual con streaming de resultados"""
        start_time = time.time()
        chunk_id = str(chunk_data["_id"])

        print(f"Procesando chunk {chunk_id} con {len(chunk_data['data'])} caracteres")

        # Extraer características y detectar anomalías
        lines = chunk_data["data"].split('\n')

        # --- DETECCIÓN DE FORMATO (nueva) ---
        # Usar las primeras líneas para detectar el formato del archivo
        sample_lines = [l for l in lines[:50] if l.strip()]
        detected_format, format_metadata = format_detector.detect_format(sample_lines)
        print(f"📋 Formato detectado: {detected_format.value}")

        # Guardar formato en el chunk para uso futuro
        chunk_data["format"] = detected_format.value
        chunk_data["format_metadata"] = format_metadata

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
            normal_logs_batch = []  # Logs normales para almacenar en Qdrant

            # 1. Detectar anomalías en el batch completo (método mejorado con formato)
            anomaly_lines = []
            for line in batch:
                if not line.strip():
                    continue

                # --- PASO 0: Parsear según formato detectado ---
                parsed = format_detector.parse_structured_line(
                    line,
                    detected_format,
                    format_metadata
                )

                # --- PASO 1: Detección por formato estructurado ---
                is_anomaly_structured = parsed.get('is_anomaly', False)
                structured_reasons = parsed.get('anomaly_reason', [])
                structured_score = 0.0

                if is_anomaly_structured:
                    # Anomalía detectada por el formato (ej: label=Malicious en Bro)
                    is_anomaly_structured = True
                    structured_score = -0.5  # Score alto para anomalías estructuradas
                    print(f"🔴 Anomalía estructural: {line[:80]}... Razón: {structured_reasons}")

                # --- PASO 2: Detección rápida por keywords ---
                is_anomaly_keywords = False
                keyword_score = 0.0

                if not is_anomaly_structured:
                    suspicious_keywords = ['error', 'failed', 'unauthorized', 'exception', 'timeout', 'denied', 'critical', 'fatal', 'warning']
                    keyword_count = sum(1 for keyword in suspicious_keywords if keyword in line.lower())

                    if keyword_count > 0:
                        is_anomaly_keywords = True
                        keyword_score = -0.1 * keyword_count

                    # Verificar patrones inusuales
                    if not is_anomaly_keywords:
                        if len(re.findall(r'[A-Z]', line)) > len(line) * 0.3:
                            is_anomaly_keywords = True
                            keyword_score = -0.05
                        elif len(line) > 500 or len(line) < 20:
                            is_anomaly_keywords = True
                            keyword_score = -0.03
                        elif any(pattern in line.lower() for pattern in ['/admin', '/login', '/wp-admin', '/.env']):
                            is_anomaly_keywords = True
                            keyword_score = -0.08

                # --- PASO 3: Detección por similitud vectorial (embeddings) ---
                # Solo si no fue detectado por estructura o keywords y hay job_id
                # Muestrear para reducir llamadas a Qdrant (1 de cada N líneas)
                is_anomaly_embeddings = False
                embedding_score = 0.0
                similar_logs = []
                detection_method = "unknown"  # Valor por defecto, puede ser sobrescrito por embeddings

                if job_id and not is_anomaly_structured and not is_anomaly_keywords:
                    self._line_counter += 1
                    # Solo usar embeddings para 1 de cada N líneas (muestreo)
                    if self._line_counter % self.embedding_sample_rate == 0:
                        is_anomaly_embeddings, embedding_score, similar_logs, detection_method = await self._detect_anomaly_with_embeddings(line, job_id)

                # --- PASO 4: Combinar resultados (OR lógico) ---
                is_anomaly = is_anomaly_structured or is_anomaly_keywords or is_anomaly_embeddings

                # Score: usar el más bajo (más anómalo) entre los métodos
                if is_anomaly_structured:
                    score = structured_score
                elif is_anomaly_keywords and is_anomaly_embeddings:
                    score = min(keyword_score, -embedding_score)
                elif is_anomaly_keywords:
                    score = keyword_score
                elif is_anomaly_embeddings:
                    score = -embedding_score
                else:
                    score = 0.0

                if is_anomaly:
                    # Agregar contexto del formato si está disponible
                    enhanced_line = line
                    if parsed.get('fields'):
                        field_info = []
                        for key, value in parsed['fields'].items():
                            if value and value != '-':
                                field_info.append(f"{key}={value}")
                        if field_info:
                            enhanced_line = f"{line} [Fields: {', '.join(field_info[:5])}]"

                    # Agregar similar_logs para contexto en la explicación
                    # detection_method se determina según qué método detectó la anomalía
                    if is_anomaly_structured or structured_score < 0:
                        detection_method = "structured_pattern"
                    elif is_anomaly_embeddings or embedding_score < 0:
                        detection_method = "embedding_similarity"
                    elif keyword_count > 0:
                        detection_method = "keyword_analysis"
                    elif parsed.get('is_anomaly', False):
                        detection_method = "field_analysis"
                    else:
                        detection_method = "unknown"

                    anomaly_data = (enhanced_line, score, detection_method)
                    if similar_logs:
                        anomaly_lines.append((anomaly_data, similar_logs))
                    else:
                        anomaly_lines.append((anomaly_data, []))
                else:
                    # Log normal: acumular para almacenar en Qdrant
                    normal_logs_batch.append(line)

                    processed_lines += 1
            
            # 2. Almacenar logs normales en Qdrant (para futura comparación)
            if normal_logs_batch:
                await self._store_normal_logs_batch(normal_logs_batch, job_id)

            # 3. Procesar anomalías en lotes con LLM (solo si hay anomalías)
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

                    # Extraer (line, score, detection_method) para cada anomalía
                    # similar_logs se usa para contexto
                    anomaly_info_list = []
                    llm_input = []
                    for anomaly_data, similar_logs in llm_batch:
                        # anomaly_data ahora es (line, score, detection_method)
                        line = anomaly_data[0]
                        score = anomaly_data[1]
                        detection_method = anomaly_data[2] if len(anomaly_data) > 2 else "unknown"
                        anomaly_info_list.append((line, score, detection_method, similar_logs))
                        llm_input.append((line, score))

                    # Obtener explicaciones para todo el lote de una vez
                    explanations = await explanation_service.get_batch_explanations(llm_input)
                    print(f"Explicaciones obtenidas: {len(explanations)}")

                    # Crear resultados para cada anomalía
                    for anomaly_info, explanation in zip(anomaly_info_list, explanations):
                        # anomaly_info es (line, score, detection_method, similar_logs)
                        line = anomaly_info[0]
                        score = anomaly_info[1]
                        detection_method = anomaly_info[2]
                        similar_logs = anomaly_info[3]

                        # Generar ID único para la anomalía
                        anomaly_id = str(uuid.uuid4())

                        # Agregar contexto de logs similares a la explicación
                        context_note = ""
                        if similar_logs:
                            context_note = f"\n\n[Contexto: Se encontraron {len(similar_logs)} logs normales similares con score máximo de {max(l['similarity_score'] for l in similar_logs):.2f}]"

                        # Agregar información del método de detección
                        method_note = f"\n\n[Método de detección: {detection_method}]"
                        if detection_method == "qdrant_global":
                            method_note += " - Búsqueda global acumulativa (≥100 logs normales)"
                        elif detection_method == "qdrant_job":
                            method_note += " - Búsqueda específica del job actual"
                        elif detection_method == "isolation_forest_fallback":
                            method_note += " - Fallback: Datos insuficientes para análisis vectorial"
                        elif detection_method == "structured_pattern":
                            method_note += " - Análisis de estructura y patrones"
                        elif detection_method == "keyword_analysis":
                            method_note += " - Palabras clave sospechosas"
                        elif detection_method == "field_analysis":
                            method_note += " - Análisis de campos anómalos"

                        enhanced_explanation = explanation + context_note + method_note

                        anomaly_result = AnomalyResultV2(
                            log_entry=line,
                            score=score,
                            is_anomaly=True,
                            explanation=enhanced_explanation,
                            chunk_id=chunk_id,
                            detection_method=detection_method,
                            severity="medium"  # Default, se puede mejorar con evaluadores individualmente
                        )
                        batch_anomalies.append(anomaly_result)
                        anomalies.append(anomaly_result)

                        # Almacenar anomalía en Qdrant para correlación futura
                        await self._store_anomaly_in_qdrant(line, score, anomaly_id, job_id)

                    print(f"Lote procesado, total anomalías: {len(anomalies)}")

                total_anomalies_processed += len(anomaly_lines)
            else:
                print(f"No hay anomalías para procesar en chunk {chunk_id}")

            # 4. Guardar batch inmediatamente para evitar pérdida de datos
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
            # Obtener project_id y workspace_id del job para usar credenciales correctas
            project_id = None
            workspace_id = None

            async with db_manager.postgres_pool.acquire() as conn:
                job = await conn.fetchrow("""
                    SELECT project_id FROM processing.processing_jobs
                    WHERE id = $1
                """, file_id)

                if job and job.get('project_id'):
                    project_id = job['project_id']
                    # Obtener workspace_id del proyecto (la columna se llama 'id' en auth.projects)
                    project = await conn.fetchrow("""
                        SELECT workspace_id FROM auth.projects
                        WHERE id = $1
                    """, project_id)
                    workspace_id = str(project['workspace_id']) if project else None

            if not project_id or not workspace_id:
                print(f"⚠️  No se encontró project_id o workspace_id para el job {file_id}")
            else:
                print(f"📋 Procesando con workspace_id: {workspace_id}, project_id: {project_id}")

            # Establecer workspace_id en services para usar credenciales correctas
            if workspace_id:
                from services.explanation_service import explanation_service
                from services.evaluator.evaluator_service import evaluator_service
                explanation_service.set_workspace_id(workspace_id)
                evaluator_service.workspace_id = workspace_id
                print(f"✅ Workspace ID establecido en services: {workspace_id}")

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

            # Calcular total de anomalías encontradas
            total_anomalies = sum(len(r.anomalies) for r in results)

            # Publicar evento de completado con estadísticas
            await self._publish_job_completed(file_id, total_anomalies)

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
    
    async def _publish_job_completed(self, job_id: str, total_anomalies: int = 0):
        """Publica evento de job completado con estadísticas finales"""
        try:
            completion_data = {
                "type": "job_completed",
                "job_id": job_id,
                "total_anomalies": total_anomalies,
                "progress": 100,
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
                        UPDATE processing.processing_jobs 
                        SET status = $1, completed_at = $2 
                        WHERE id = $3
                    """, status, datetime.utcnow(), file_id)
                else:
                    await conn.execute("""
                        UPDATE processing.processing_jobs 
                        SET status = $1 
                        WHERE id = $2
                    """, status, file_id)
                print(f"Estado del job {file_id} actualizado a {status}")
        except Exception as e:
            print(f"Error actualizando estado del job: {e}")

worker_service = WorkerService()
