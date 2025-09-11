import json
import os
import re
import math
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest
import requests

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Anomaly Detector Service",
    description="Servicio para detectar anomalías en logs usando Isolation Forest y explicaciones con LLM",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger para la aplicación
logger = logging.getLogger("anomaly_detector")

# Configuración
OLLAMA_SERVICE_URL = os.getenv("OLLAMA_SERVICE_URL", "http://ollama-service:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "nidum-gemma-2b-uncensored-gguf")

# Directorios base
APP_DIR = "/app"
REPORTS_DIR = os.path.join(APP_DIR, "reports")
CHUNKS_DIR = os.path.join(APP_DIR, "chunks")

# Crear directorios si no existen
for dir_path in [REPORTS_DIR, CHUNKS_DIR]:
    try:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Directorio asegurado: {dir_path}")
    except Exception as e:
        logger.error(f"Error creando directorio {dir_path}: {e}")

# Listar contenido de directorios para debug
try:
    logger.info("=== Estado de Directorios ===")
    logger.info(f"APP_DIR ({APP_DIR}):")
    logger.info(os.listdir(APP_DIR))
    logger.info(f"\nREPORTS_DIR ({REPORTS_DIR}):")
    logger.info(os.listdir(REPORTS_DIR))
    logger.info(f"\nCHUNKS_DIR ({CHUNKS_DIR}):")
    logger.info(os.listdir(CHUNKS_DIR))
except Exception as e:
    logger.error(f"Error listando directorios: {e}")

# Modelos Pydantic
class LogEntry(BaseModel):
    content: str
    timestamp: Optional[str] = None

class AnomalyResult(BaseModel):
    log_entry: str
    anomaly_score: float
    is_anomaly: bool
    explanation: str

class ChunkInfo(BaseModel):
    filename: str
    file_id: str

class DetectionResponse(BaseModel):
    total_logs: int
    anomalies_detected: int
    anomalies: List[AnomalyResult]
    report_file: str
    chunk_info: Optional[ChunkInfo] = None

class HealthResponse(BaseModel):
    status: str

# Funciones de extracción de características
def extract_features(log_text: str) -> List[float]:
    """Extrae características numéricas de un log entry"""
    features = []
    
    # Longitud del log
    features.append(len(log_text))
    
    # Número de palabras
    words = log_text.split()
    features.append(len(words))
    
    # Entropía del texto
    if log_text:
        char_counts = {}
        for char in log_text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        entropy = 0
        for count in char_counts.values():
            p = count / len(log_text)
            if p > 0:
                entropy -= p * math.log2(p)
        features.append(entropy)
    else:
        features.append(0)
    
    # Presencia de palabras clave sospechosas
    suspicious_keywords = ['error', 'failed', 'unauthorized', 'exception', 'timeout', 'denied', 'critical']
    keyword_count = sum(1 for keyword in suspicious_keywords if keyword.lower() in log_text.lower())
    features.append(keyword_count)
    
    # Número de caracteres especiales
    special_chars = len(re.findall(r'[!@#$%^&*(),.?":{}|<>]', log_text))
    features.append(special_chars)
    
    # Número de números en el log
    numbers = len(re.findall(r'\d+', log_text))
    features.append(numbers)
    
    # Longitud promedio de palabras
    if words:
        avg_word_length = sum(len(word) for word in words) / len(words)
        features.append(avg_word_length)
    else:
        features.append(0)
    
    return features

def detect_anomalies(log_entries: List[str]) -> tuple:
    """Detecta anomalías usando Isolation Forest"""
    logger.info("=== Iniciando Detección de Anomalías ===")
    logger.info(f"Procesando {len(log_entries)} logs")
    
    if len(log_entries) < 2:
        logger.warning("Insuficientes logs para análisis (mínimo 2 requeridos)")
        return [], []
    
    # Extraer características
    logger.info("Extrayendo características de los logs...")
    features_matrix = []
    for i, log_entry in enumerate(log_entries, 1):
        features = extract_features(log_entry)
        features_matrix.append(features)
        
        # Mostrar progreso cada 1000 logs
        if i % 1000 == 0:
            logger.info(f"Procesados {i}/{len(log_entries)} logs")
    
    # Convertir a DataFrame
    df = pd.DataFrame(features_matrix)
    
    # Entrenar Isolation Forest
    logger.info("Entrenando modelo Isolation Forest...")
    logger.info("Configuración del modelo:")
    logger.info("- Contaminación esperada: 10%")
    logger.info("- Número de estimadores: 100")
    
    isolation_forest = IsolationForest(
        contamination=0.1,  # 10% de anomalías esperadas
        random_state=42,
        n_estimators=100
    )
    
    anomaly_labels = isolation_forest.fit_predict(df)
    anomaly_scores = isolation_forest.decision_function(df)
    
    # Análisis de resultados
    n_anomalies = sum(1 for label in anomaly_labels if label == -1)
    anomaly_percentage = (n_anomalies / len(log_entries)) * 100
    
    logger.info("Resultados del análisis:")
    logger.info(f"- Total de logs analizados: {len(log_entries)}")
    logger.info(f"- Anomalías detectadas: {n_anomalies} ({anomaly_percentage:.2f}%)")
    logger.info(f"- Score promedio: {np.mean(anomaly_scores):.4f}")
    logger.info(f"- Score mínimo: {np.min(anomaly_scores):.4f}")
    logger.info(f"- Score máximo: {np.max(anomaly_scores):.4f}")
    logger.info("=== Fin de Detección de Anomalías ===")
    
    return anomaly_labels, anomaly_scores

async def get_llm_explanation(log_entry: str) -> str:
    """Obtiene explicación del LLM para un log anómalo"""
    try:
        logger.info("=== Análisis de Log Sospechoso ===")
        logger.debug(f"Log a analizar: {log_entry}")
        
        # Extraer información básica del log
        components = log_entry.split()
        log_info = {
            "Servidor": components[0] if len(components) > 0 else 'N/A',
            "IP": components[1] if len(components) > 1 else 'N/A',
            "Método": components[6].strip('\"') if len(components) > 6 else 'N/A',
            "Ruta": components[7] if len(components) > 7 else 'N/A',
            "Código": components[9] if len(components) > 9 else 'N/A'
        }
        
        logger.info("Componentes del log:")
        for key, value in log_info.items():
            logger.info(f"- {key}: {value}")
        
        prompt = f"""Analiza este log y clasifica la anomalía.
        REGLAS ESTRICTAS:
        1. Usa SOLO estos tipos de alerta: [ACCESO_INVÁLIDO], [ERROR_AUTENTICACIÓN], [COMPORTAMIENTO_INUSUAL], [RUTA_SOSPECHOSA], [MÉTODO_INCORRECTO]
        2. La explicación DEBE tener máximo 10 palabras
        3. Sigue EXACTAMENTE este formato: [TIPO_ALERTA] - [EXPLICACIÓN CORTA]
        
        Log: {log_entry}
        """
        
        logger.debug("Prompt enviado al LLM:")
        logger.debug(prompt)
        
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3  # Reducimos temperatura para respuestas más concisas
            }
        }
        
        response = requests.post(
            f"{OLLAMA_SERVICE_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            explanation = result.get("response", "No se pudo generar explicación")
            
            logger.info("Respuesta del LLM:")
            logger.info(explanation)
            
            # Analizar la respuesta
            if '[' in explanation and ']' in explanation:
                alert_type = explanation.split(']')[0].strip('[')
                logger.info(f"Tipo de alerta identificada: {alert_type}")
                
                # Evaluar severidad basada en palabras clave
                severity_keywords = {
                    'CRÍTICO': ['unauthorized', 'attack', 'breach', 'exploit', 'injection'],
                    'ALTO': ['error', 'failed', 'invalid', 'denied', 'timeout'],
                    'MEDIO': ['warning', 'retry', 'degraded', 'slow'],
                    'BAJO': ['notice', 'info', 'debug']
                }
                
                severity = 'DESCONOCIDO'
                for level, keywords in severity_keywords.items():
                    if any(keyword in explanation.lower() for keyword in keywords):
                        severity = level
                        break
                
                logger.info(f"Nivel de severidad estimado: {severity}")
                
                # Log detallado para debugging
                logger.debug("Detalles del análisis:", extra={
                    'alert_type': alert_type,
                    'severity': severity,
                    'keywords_found': [k for k in sum(severity_keywords.values(), []) if k in explanation.lower()]
                })
            
            logger.info("=== Fin del Análisis ===")
            return explanation
        else:
            error_msg = f"Error al conectar con LLM: {response.status_code}"
            print(f"\nError: {error_msg}")
            return error_msg
            
    except Exception as e:
        return f"Error al obtener explicación del LLM: {str(e)}"

def save_report(results: Dict[str, Any], file_id: str = None) -> str:
    """Guarda el reporte en un archivo JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if file_id:
        # Si es un chunk, guardar en el directorio del archivo original
        report_name = f"{file_id}_report_{timestamp}.json"
        report_dir = os.path.join(CHUNKS_DIR, file_id)
        os.makedirs(report_dir, exist_ok=True)
        filepath = os.path.join(report_dir, report_name)
    else:
        # Reporte normal
        report_name = f"report-{timestamp}.json"
        filepath = os.path.join(REPORTS_DIR, report_name)
    
    logger.info(f"Guardando reporte en: {filepath}")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Reporte guardado exitosamente")
    
    return report_name

# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok")

@app.get("/reports")
async def list_reports():
    """Lista todos los reportes disponibles"""
    reports = []
    
    logger.info(f"Buscando reportes en: {CHUNKS_DIR}")
    
    try:
        # Verificar que el directorio existe
        if not os.path.exists(CHUNKS_DIR):
            logger.warning(f"El directorio {CHUNKS_DIR} no existe")
            return []
        
        # Listar contenido del directorio
        dir_contents = os.listdir(CHUNKS_DIR)
        logger.info(f"Contenido del directorio: {dir_contents}")
        
        # Buscar en todos los directorios de chunks
        for chunk_dir in dir_contents:
            chunk_path = os.path.join(CHUNKS_DIR, chunk_dir)
            logger.info(f"Revisando directorio: {chunk_path}")
            
            if os.path.isdir(chunk_path):
                # Listar archivos en el directorio de chunks
                chunk_files = os.listdir(chunk_path)
                logger.info(f"Archivos en {chunk_dir}: {chunk_files}")
                
            # Buscar archivos de reporte
            for file in sorted(chunk_files, reverse=True):  # Ordenar por nombre para obtener el más reciente
                # Buscar archivos de reporte por patrón
                if '_report_' in file and file.endswith('.json'):
                    logger.debug(f"Encontrado archivo de reporte: {file}")
                    report_path = os.path.join(chunk_path, file)
                    logger.info(f"Procesando reporte: {report_path}")
                    
                    try:
                        with open(report_path, 'r', encoding='utf-8') as f:
                            report_data = json.load(f)
                            # Agregar información del archivo y directorio
                            report_data['report_file'] = file
                            report_data['file_id'] = chunk_dir
                            report_data['timestamp'] = datetime.strptime(
                                file.split('_report_')[1].replace('.json', ''),
                                '%Y%m%d_%H%M%S'
                            ).isoformat()
                            reports.append(report_data)
                            logger.info(f"Reporte agregado: {file}")
                    except Exception as e:
                        logger.error(f"Error leyendo reporte {report_path}: {e}")
    except Exception as e:
        logger.error(f"Error listando reportes: {e}")
        return []
    
    # Ordenar por timestamp más reciente
    reports.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    logger.info(f"Total de reportes encontrados: {len(reports)}")
    return reports

async def process_anomalies_batch(log_entries: List[str], anomaly_indices: List[int], 
                               anomaly_scores: List[float], batch_start: int, 
                               batch_size: int, file_id: str) -> Dict:
    """Procesa un lote de anomalías y retorna los resultados"""
    batch_end = min(batch_start + batch_size, len(anomaly_indices))
    batch_indices = anomaly_indices[batch_start:batch_end]
    
    # Crear tareas para el lote actual
    batch_tasks = []
    for idx in batch_indices:
        batch_tasks.append(get_llm_explanation(log_entries[idx]))
    
    # Procesar explicaciones en paralelo
    batch_explanations = await asyncio.gather(*batch_tasks)
    
    # Crear resultados del lote
    batch_anomalies = []
    for idx, explanation in zip(batch_indices, batch_explanations):
        anomaly_result = AnomalyResult(
            log_entry=log_entries[idx],
            anomaly_score=float(anomaly_scores[idx]),
            is_anomaly=True,
            explanation=explanation
        )
        batch_anomalies.append(anomaly_result)
    
    # Crear respuesta parcial
    progress = min(100, (batch_end / len(anomaly_indices)) * 100)
    response_data = {
        "total_logs": len(log_entries),
        "anomalies_detected": len(anomaly_indices),
        "anomalies": [anomaly.dict() for anomaly in batch_anomalies],
        "processed_percentage": progress,
        "is_complete": batch_end >= len(anomaly_indices),
        "timestamp": datetime.now().isoformat()
    }
    
    # Guardar reporte parcial
    report_file = save_report(response_data, file_id)
    response_data["report_file"] = report_file
    
    return response_data

@app.post("/detect")
async def detect_anomalies_endpoint(file: UploadFile = File(...)):
    """
    Detecta anomalías en un archivo de logs con streaming de resultados
    """
    try:
        print(f"\n=== Nuevo archivo recibido ===")
        print(f"Nombre del archivo: {file.filename}")
        print(f"Tipo de contenido: {file.content_type}")
        print(f"Tamaño del archivo: {len(await file.read())} bytes")
        await file.seek(0)  # Resetear el cursor del archivo después de leerlo
        
        # Extraer información del nombre del archivo
        filename = file.filename
        print(f"Analizando nombre del archivo: {filename}")
        file_id = filename.split('_chunk')[0] if '_chunk' in filename else filename
        print(f"ID extraído: {file_id}")
        
        # Crear directorio específico para este archivo si no existe
        file_chunks_dir = os.path.join(CHUNKS_DIR, file_id)
        os.makedirs(file_chunks_dir, exist_ok=True)
        
        # Guardar el chunk
        chunk_path = os.path.join(file_chunks_dir, filename)
        print(f"Guardando chunk en: {chunk_path}")
        content = await file.read()
        print(f"Contenido leído: {len(content)} bytes")
        print(f"Primeros 100 caracteres del contenido:")
        print(content[:100].decode('utf-8', errors='ignore'))
        
        with open(chunk_path, 'wb') as f:
            f.write(content)
        print(f"Chunk guardado exitosamente")
        
        # Leer contenido para procesamiento
        text_content = content.decode('utf-8')
        
        # Parsear logs (asumir una línea por log entry)
        log_entries = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        if not log_entries:
            raise HTTPException(status_code=400, detail="El archivo no contiene logs válidos")
        
        # Detectar anomalías
        anomaly_labels, anomaly_scores = detect_anomalies(log_entries)
        
        # Identificar índices de anomalías
        anomaly_indices = [i for i, label in enumerate(anomaly_labels) if label == -1]
        
        if not anomaly_indices:
            return DetectionResponse(
                total_logs=len(log_entries),
                anomalies_detected=0,
                anomalies=[],
                report_file="no_anomalies.json",
                chunk_info={"filename": filename, "file_id": file_id}
            )
        
        # Configuración de procesamiento por lotes
        BATCH_SIZE = 5  # Procesar 5 anomalías a la vez
        
        async def generate_results():
            for batch_start in range(0, len(anomaly_indices), BATCH_SIZE):
                batch_results = await process_anomalies_batch(
                    log_entries, anomaly_indices, anomaly_scores,
                    batch_start, BATCH_SIZE, file_id
                )
                
                # Agregar información del chunk
                batch_results["chunk_info"] = {
                    "filename": filename,
                    "file_id": file_id
                }
                
                # Enviar resultados parciales
                yield json.dumps(batch_results) + "\n"
                
                # Pequeña pausa para permitir que nginx procese
                await asyncio.sleep(0.1)
        
        return StreamingResponse(
            generate_results(),
            media_type="application/x-ndjson"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando logs: {str(e)}")

@app.post("/detect-text", response_model=DetectionResponse)
async def detect_anomalies_from_text(logs: List[LogEntry]):
    """
    Detecta anomalías en una lista de logs enviados como JSON
    """
    try:
        if not logs:
            raise HTTPException(status_code=400, detail="No se proporcionaron logs")
        
        # Extraer contenido de los logs
        log_entries = [log.content for log in logs]
        
        # Detectar anomalías
        anomaly_labels, anomaly_scores = detect_anomalies(log_entries)
        
        # Procesar resultados
        anomalies = []
        for i, (log_entry, label, score) in enumerate(zip(log_entries, anomaly_labels, anomaly_scores)):
            if label == -1:  # Anomalía detectada
                explanation = await get_llm_explanation(log_entry)
                anomaly_result = AnomalyResult(
                    log_entry=log_entry,
                    anomaly_score=float(score),
                    is_anomaly=True,
                    explanation=explanation
                )
                anomalies.append(anomaly_result)
        
        # Crear respuesta
        response_data = {
            "total_logs": len(log_entries),
            "anomalies_detected": len(anomalies),
            "anomalies": [anomaly.dict() for anomaly in anomalies],
            "timestamp": datetime.now().isoformat()
        }
        
        # Guardar reporte
        report_file = save_report(response_data)
        response_data["report_file"] = report_file
        
        return DetectionResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando logs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
