-- Script de inicialización para PostgreSQL V2
-- Crear base de datos y tablas necesarias para la arquitectura multi-DB

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS logsanomaly;

-- Usar la base de datos
\c logsanomaly;

-- Crear usuario si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'anomaly_user') THEN
        CREATE ROLE anomaly_user WITH LOGIN PASSWORD 'anomaly_password';
    END IF;
END
$$;

-- Otorgar permisos
GRANT ALL PRIVILEGES ON DATABASE logsanomaly TO anomaly_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO anomaly_user;

-- Crear tabla de jobs de procesamiento
CREATE TABLE IF NOT EXISTS processing_jobs (
    id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    total_size INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunks_processed INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de estadísticas de procesamiento
CREATE TABLE IF NOT EXISTS processing_stats (
    id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    chunk_number INTEGER NOT NULL,
    processing_time FLOAT NOT NULL,
    anomalies_found INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES processing_jobs(id) ON DELETE CASCADE
);

-- Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_filename ON processing_jobs(filename);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON processing_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_stats_job_id ON processing_stats(job_id);
CREATE INDEX IF NOT EXISTS idx_stats_chunk_number ON processing_stats(chunk_number);

-- Otorgar permisos en las tablas
GRANT ALL PRIVILEGES ON TABLE processing_jobs TO anomaly_user;
GRANT ALL PRIVILEGES ON TABLE processing_stats TO anomaly_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO anomaly_user;

-- Insertar datos de prueba (opcional)
INSERT INTO processing_jobs (id, filename, total_size, total_chunks, status) 
VALUES ('test-job-001', 'test_logs.txt', 1024, 1, 'completed')
ON CONFLICT (id) DO NOTHING;

-- Mostrar información de las tablas creadas
\dt
\d processing_jobs
\d processing_stats

-- Mostrar datos de prueba
SELECT * FROM processing_jobs LIMIT 5;
SELECT * FROM processing_stats LIMIT 5;
