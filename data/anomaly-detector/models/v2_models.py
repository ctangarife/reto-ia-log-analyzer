from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ChunkData(BaseModel):
    file_id: str
    chunk_number: int
    data: str
    size: int
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessingJob(BaseModel):
    id: str
    filename: str
    total_size: int
    total_chunks: int
    chunks_processed: int = 0
    status: ProcessingStatus = ProcessingStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class ProcessingStats(BaseModel):
    id: str
    job_id: str
    chunk_number: int
    processing_time: float
    anomalies_found: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnomalyResultV2(BaseModel):
    log_entry: str
    score: float  # Cambiado de anomaly_score a score
    is_anomaly: bool
    explanation: str
    chunk_id: str

class ChunkResult(BaseModel):
    chunk_id: str
    anomalies: List[AnomalyResultV2]
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessResponseV2(BaseModel):
    job_id: str
    status: ProcessingStatus
    message: str
    total_chunks: int
    estimated_time: Optional[int] = None

class StatusResponseV2(BaseModel):
    job_id: str
    status: ProcessingStatus
    progress: float  # 0.0 a 1.0
    chunks_processed: int
    total_chunks: int
    anomalies_found: int
    estimated_remaining_time: Optional[int] = None
    error_message: Optional[str] = None

class StreamResult(BaseModel):
    chunk_number: int
    anomalies: List[AnomalyResultV2]
    progress: float
    is_complete: bool
