-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Tabla de trabajos de procesamiento
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    total_size BIGINT NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunks_processed INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de estadísticas de procesamiento
CREATE TABLE IF NOT EXISTS processing_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES processing_jobs(id),
    chunk_number INTEGER NOT NULL,
    processing_time FLOAT,
    anomalies_found INTEGER DEFAULT 0,
    memory_used BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de configuraciones
CREATE TABLE IF NOT EXISTS configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    contamination FLOAT DEFAULT 0.1,
    n_estimators INTEGER DEFAULT 100,
    random_state INTEGER DEFAULT 42,
    suspicious_keywords JSONB,
    model_params JSONB,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_filename ON processing_jobs(filename);
CREATE INDEX IF NOT EXISTS idx_stats_job_id ON processing_stats(job_id);
CREATE INDEX IF NOT EXISTS idx_config_active ON configurations(is_active);

-- Configuración inicial por defecto
INSERT INTO configurations (
    name, 
    description, 
    suspicious_keywords,
    is_active
) VALUES (
    'default',
    'Configuración por defecto del sistema',
    '["error", "failed", "unauthorized", "exception", "timeout", "denied", "critical", "fatal", "panic", "abort"]',
    true
) ON CONFLICT (name) DO NOTHING;
