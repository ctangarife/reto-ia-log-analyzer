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

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from middleware.auth_middleware import get_current_user_optional

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
from services import qdrant_service

# Imports de rutas
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.workspaces import router as workspaces_router
from routes.projects import router as projects_router
from routes.course import router as course_router, workspace_router
from routes.course_generation import router as course_generation_router
from routes.course_rbac import router as course_rbac_router
from routes.lesson_edit import router as lesson_edit_router
from routes.llm_config import router as llm_config_router

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
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins:
    # Fallback a localhost para desarrollo
    allowed_origins = ["http://localhost:8080", "http://localhost"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Modelos Pydantic
class HealthResponse:
    status: str

# === INICIALIZACIÓN DE BASES DE DATOS ===
@app.on_event("startup")
async def startup_event():
    """Inicializar conexiones a bases de datos y precargar modelos"""
    try:
        await db_manager.connect_all()
        logger.info("✅ Todas las bases de datos conectadas")

        # Inicializar servicio de monitoreo
        monitoring_service.set_services(db_manager, worker_service)
        asyncio.create_task(monitoring_service.start_monitoring(interval=30))
        logger.info("✅ Servicio de monitoreo iniciado")

        # Precargar modelo de embeddings para evitar timeout en primera petición
        from services.embedding_service import preload_model
        try:
            preload_model()  # Esto descargará el modelo si no existe en cache
            logger.info("✅ Modelo de embeddings precargado")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo precargar el modelo de embeddings: {e}")
            logger.warning("⚠️  El modelo se descargará en la primera petición (puede causar latencia)")

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
app.include_router(course_router)
app.include_router(workspace_router)
app.include_router(course_generation_router)
app.include_router(course_rbac_router)
app.include_router(lesson_edit_router)
app.include_router(llm_config_router)

# === ENDPOINTS ===

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/admin/init-learning-schema")
async def init_learning_schema():
    """
    Inicializa el esquema learning y sus tablas con la estructura completa.
    Incluye flujo de trabajo de cursos (draft, pending, published, etc.)
    y generación dinámica basada en anomalías del proyecto.

    Para bases de datos existentes que no tienen el schema learning.
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Verificar si el schema ya existe
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning')"
            )

            if schema_exists:
                # Verificar si tiene la estructura nueva
                has_workflow_fields = await conn.fetchval("""
                    SELECT EXISTS(SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'learning' AND table_name = 'course_modules' AND column_name = 'status')
                """)

                if has_workflow_fields:
                    return {
                        "status": "already_exists",
                        "message": "El esquema learning ya existe con la estructura actualizada."
                    }
                else:
                    return {
                        "status": "needs_migration",
                        "message": "El esquema learning existe pero necesita migración. Ejecuta POST /admin/migrate-learning-schema"
                    }

            # Crear el esquema y tablas
            await conn.execute("CREATE SCHEMA IF NOT EXISTS learning")

            # Crear tabla course_modules (con campos de flujo de trabajo)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_modules (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    project_id UUID,  -- NULL para cursos de workspace
                    workspace_id UUID,
                    module_order INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    -- Flujo de trabajo
                    status VARCHAR(20) DEFAULT 'draft',
                    scope VARCHAR(20) DEFAULT 'project',
                    version_number INT DEFAULT 1,
                    created_by UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by UUID,
                    reviewed_at TIMESTAMP,
                    published_at TIMESTAMP,
                    archived_at TIMESTAMP,
                    rejection_reason TEXT,
                    change_description TEXT,
                    UNIQUE(project_id, module_order)
                )
            """)

            # Crear tabla course_lessons (con soporte para lecciones dinámicas)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_lessons (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    module_id UUID NOT NULL REFERENCES learning.course_modules(id) ON DELETE CASCADE,
                    lesson_order INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,  -- NULL para lecciones dinámicas
                    exercise_data JSONB,
                    is_dynamic BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(module_id, lesson_order)
                )
            """)

            # Crear tabla lesson_progress
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.lesson_progress (
                    user_id UUID NOT NULL,
                    project_id UUID NOT NULL,
                    workspace_id UUID,
                    lesson_id UUID NOT NULL REFERENCES learning.course_lessons(id) ON DELETE CASCADE,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    score INT,
                    attempts INT DEFAULT 0,
                    PRIMARY KEY (user_id, project_id, lesson_id)
                )
            """)

            # Crear tabla course_completion
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_completion (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL,
                    project_id UUID NOT NULL,
                    workspace_id UUID,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_score INT DEFAULT 0,
                    badge_earned BOOLEAN DEFAULT TRUE,
                    certificate_url VARCHAR(500),
                    UNIQUE(user_id, project_id)
                )
            """)

            # Crear tabla exercise_attempts
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.exercise_attempts (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL,
                    project_id UUID NOT NULL,
                    workspace_id UUID,
                    lesson_id UUID NOT NULL REFERENCES learning.course_lessons(id) ON DELETE CASCADE,
                    anomaly_id VARCHAR(255),
                    user_answer JSONB NOT NULL,
                    is_correct BOOLEAN,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Crear tabla course_reviews
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_reviews (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    course_id UUID NOT NULL,
                    reviewer_id UUID NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    comments TEXT,
                    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version_number INT NOT NULL
                )
            """)

            # Crear tabla course_versions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_versions (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    course_module_id UUID NOT NULL,
                    version_number INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_by UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_description TEXT,
                    UNIQUE(course_module_id, version_number)
                )
            """)

            # Crear tabla course_notifications
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_notifications (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    workspace_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    course_id UUID,
                    type VARCHAR(50) NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Crear tabla lesson_change_history
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.lesson_change_history (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    lesson_id UUID NOT NULL,
                    changed_by UUID NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_type VARCHAR(50) NOT NULL,
                    change_description TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    is_minor_edit BOOLEAN DEFAULT FALSE
                )
            """)

            # Crear índices
            await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS lesson_progress_user_lesson_uk ON learning.lesson_progress(user_id, lesson_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_user ON learning.lesson_progress(user_id, project_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_lesson ON learning.lesson_progress(lesson_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_exercise_attempts_user ON learning.exercise_attempts(user_id, project_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_modules_workspace ON learning.course_modules(workspace_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_completion_user ON learning.course_completion(user_id, project_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_reviews_course ON learning.course_reviews(course_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_versions_module ON learning.course_versions(course_module_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_notifications_workspace ON learning.course_notifications(workspace_id, user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_notifications_unread ON learning.course_notifications(user_id, is_read)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_change_history_lesson ON learning.lesson_change_history(lesson_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_change_history_changed_by ON learning.lesson_change_history(changed_by)")

            # Otorgar permisos
            await conn.execute("GRANT USAGE ON SCHEMA learning TO anomaly_user")
            await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA learning TO anomaly_user")
            await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA learning TO anomaly_user")

            logger.info("✅ Esquema learning inicializado correctamente")

            return {
                "status": "success",
                "message": "Esquema learning y tablas creadas exitosamente con flujo de trabajo completo."
            }

    except Exception as e:
        logger.error(f"Error inicializando esquema learning: {e}")
        raise HTTPException(status_code=500, detail=f"Error al inicializar el esquema: {str(e)}")

@app.post("/admin/migrate-learning-schema")
async def migrate_learning_schema():
    """
    Migra el esquema learning existente para agregar:
    - workspace_id como referencia
    - Campos de flujo de trabajo (status, scope, version_number, etc.)
    - Nuevas tablas (course_reviews, course_versions, course_notifications)
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Verificar si el schema existe
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning')"
            )

            if not schema_exists:
                raise HTTPException(
                    status_code=404,
                    detail="El esquema learning no existe. Ejecuta primero POST /admin/init-learning-schema"
                )

            # Migración workspace_id
            has_workspace_id = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'learning' AND table_name = 'course_modules' AND column_name = 'workspace_id')
            """)

            if not has_workspace_id:
                logger.info("Agregando workspace_id a tablas existentes...")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS workspace_id UUID")
                await conn.execute("ALTER TABLE learning.lesson_progress ADD COLUMN IF NOT EXISTS workspace_id UUID")
                await conn.execute("ALTER TABLE learning.course_completion ADD COLUMN IF NOT EXISTS workspace_id UUID")
                await conn.execute("ALTER TABLE learning.exercise_attempts ADD COLUMN IF NOT EXISTS workspace_id UUID")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_modules_workspace ON learning.course_modules(workspace_id)")

            # Migración campos de flujo de trabajo
            has_workflow_fields = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'learning' AND table_name = 'course_modules' AND column_name = 'status')
            """)

            if not has_workflow_fields:
                logger.info("Agregando campos de flujo de trabajo a course_modules...")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft'")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS scope VARCHAR(20) DEFAULT 'project'")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS version_number INT DEFAULT 1")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS created_by UUID")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS reviewed_by UUID")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS published_at TIMESTAMP")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS rejection_reason TEXT")
                await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS change_description TEXT")

                # Make project_id nullable for workspace-scoped courses
                await conn.execute("ALTER TABLE learning.course_modules ALTER COLUMN project_id DROP NOT NULL")

            # Campo is_dynamic en course_lessons
            has_dynamic_field = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'learning' AND table_name = 'course_lessons' AND column_name = 'is_dynamic')
            """)

            if not has_dynamic_field:
                logger.info("Agregando campo is_dynamic a course_lessons...")
                await conn.execute("ALTER TABLE learning.course_lessons ADD COLUMN IF NOT EXISTS is_dynamic BOOLEAN DEFAULT FALSE")
                # Make content nullable for dynamic lessons
                await conn.execute("ALTER TABLE learning.course_lessons ALTER COLUMN content DROP NOT NULL")

            # Crear nuevas tablas
            logger.info("Creando nuevas tablas de flujo de trabajo...")

            # Tabla course_reviews
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_reviews (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    course_id UUID NOT NULL,
                    reviewer_id UUID NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    comments TEXT,
                    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version_number INT NOT NULL
                )
            """)

            # Tabla course_versions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_versions (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    course_module_id UUID NOT NULL,
                    version_number INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_by UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_description TEXT,
                    UNIQUE(course_module_id, version_number)
                )
            """)

            # Tabla course_notifications
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.course_notifications (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    workspace_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    course_id UUID,
                    type VARCHAR(50) NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla lesson_change_history
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.lesson_change_history (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    lesson_id UUID NOT NULL,
                    changed_by UUID NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_type VARCHAR(50) NOT NULL,
                    change_description TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    is_minor_edit BOOLEAN DEFAULT FALSE
                )
            """)

            # Crear índices
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_reviews_course ON learning.course_reviews(course_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_versions_module ON learning.course_versions(course_module_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_notifications_workspace ON learning.course_notifications(workspace_id, user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_notifications_unread ON learning.course_notifications(user_id, is_read)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_change_history_lesson ON learning.lesson_change_history(lesson_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_lesson_change_history_changed_by ON learning.lesson_change_history(changed_by)")

            logger.info("✅ Esquema learning migrado correctamente")

            return {
                "status": "success",
                "message": "Esquema learning migrado con nuevos campos de flujo de trabajo y tablas."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error migrando esquema learning: {e}")
        raise HTTPException(status_code=500, detail=f"Error al migrar el esquema: {str(e)}")

@app.post("/admin/migrate-v2-courses-table")
async def migrate_v2_courses_table():
    """
    Migración v2: Crea la nueva tabla 'courses' separada de 'course_modules'.

    Nueva estructura:
    - courses: Entidad principal del curso (estado, versión, etc.)
    - course_modules: Hijos de courses (4 módulos fijos por curso)
    - course_lessons: Hijos de course_modules (lecciones por módulo)

    Esta migración es necesaria para usar el nuevo sistema de generación de cursos.
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Verificar si el schema learning existe
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning')"
            )

            if not schema_exists:
                raise HTTPException(
                    status_code=404,
                    detail="El esquema learning no existe. Ejecuta primero POST /admin/init-learning-schema"
                )

            # Verificar si la tabla courses ya existe
            courses_table_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = 'learning' AND table_name = 'courses')"
            )

            if courses_table_exists:
                # Verificar si tiene la columna course_id en course_modules
                has_course_id = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema = 'learning' AND table_name = 'course_modules' AND column_name = 'course_id')"
                )

                if has_course_id:
                    return {
                        "status": "already_migrated",
                        "message": "La migración v2 ya está aplicada. La tabla courses existe y course_modules tiene course_id."
                    }
                else:
                    # Agregar course_id a course_modules
                    logger.info("Agregando course_id a course_modules...")
                    await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS course_id UUID")

                    # Crear índice
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_modules_course ON learning.course_modules(course_id)")

                    return {
                        "status": "updated",
                        "message": "Se agregó course_id a course_modules. La tabla courses ya existía."
                    }

            # Crear la tabla courses
            logger.info("Creando tabla courses...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning.courses (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    project_id UUID NOT NULL,
                    workspace_id UUID NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'draft',
                    scope VARCHAR(20) DEFAULT 'project',
                    version_number INT DEFAULT 1,
                    created_by UUID NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_by UUID,
                    reviewed_at TIMESTAMP,
                    published_at TIMESTAMP,
                    archived_at TIMESTAMP,
                    rejection_reason TEXT,
                    change_description TEXT
                )
            """)

            # Agregar course_id a course_modules
            await conn.execute("ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS course_id UUID")

            # Crear índices
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_courses_project ON learning.courses(project_id, status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_courses_workspace ON learning.courses(workspace_id, status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_course_modules_course ON learning.course_modules(course_id)")

            # Crear función para validar límites de cursos
            await conn.execute("""
                CREATE OR REPLACE FUNCTION learning.validate_course_limits(
                    p_project_id UUID,
                    p_workspace_id UUID,
                    p_status VARCHAR
                ) RETURNS TABLE (
                    can_create BOOLEAN,
                    reason TEXT,
                    current_counts JSONB
                ) AS $$
                DECLARE
                    published_count INT;
                    draft_count INT;
                    pending_count INT;
                BEGIN
                    SELECT COUNT(*) INTO published_count
                    FROM learning.courses
                    WHERE project_id = p_project_id AND status = 'published';

                    SELECT COUNT(*) INTO draft_count
                    FROM learning.courses
                    WHERE project_id = p_project_id AND status = 'draft';

                    SELECT COUNT(*) INTO pending_count
                    FROM learning.courses
                    WHERE project_id = p_project_id AND status = 'pending';

                    IF p_status = 'published' AND published_count >= 1 THEN
                        RETURN QUERY SELECT FALSE, 'Ya existe un curso publicado', jsonb_build_object(
                            'published', published_count, 'draft', draft_count, 'pending', pending_count
                        );
                    ELSIF p_status = 'draft' AND draft_count >= 3 THEN
                        RETURN QUERY SELECT FALSE, 'Máximo de 3 cursos en borrador', jsonb_build_object(
                            'published', published_count, 'draft', draft_count, 'pending', pending_count
                        );
                    ELSIF p_status = 'pending' AND pending_count >= 3 THEN
                        RETURN QUERY SELECT FALSE, 'Máximo de 3 cursos pendientes', jsonb_build_object(
                            'published', published_count, 'draft', draft_count, 'pending', pending_count
                        );
                    ELSE
                        RETURN QUERY SELECT TRUE, 'Límites válidos', jsonb_build_object(
                            'published', published_count, 'draft', draft_count, 'pending', pending_count
                        );
                    END IF;
                END;
                $$ LANGUAGE plpgsql;
            """)

            # Otorgar permisos
            await conn.execute("GRANT ALL PRIVILEGES ON TABLE learning.courses TO anomaly_user")
            await conn.execute("GRANT EXECUTE ON FUNCTION learning.validate_course_limits TO anomaly_user")

            logger.info("✅ Migración v2 completada correctamente")

            return {
                "status": "success",
                "message": "Migración v2 completada. Nueva tabla courses creada con estructura separada de módulos."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en migración v2: {e}")
        raise HTTPException(status_code=500, detail=f"Error al migrar: {str(e)}")

@app.post("/process", response_model=ProcessResponseV2)
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...)
):
    """
    Procesar archivo usando arquitectura multi-DB con servicios refactorizados.
    Usa ExplanationService con Ollama Cloud para generar explicaciones.
    """
    try:
        # ========== VALIDACIONES DE SEGURIDAD ==========
        # 1. Validar tamaño de archivo
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Archivo demasiado grande. Máximo permitido: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        if len(content) == 0:
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío"
            )

        # 2. Validar project_id
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="El project_id es obligatorio. Por favor selecciona un proyecto."
            )

        # 3. Validar extensión del archivo
        ALLOWED_EXTENSIONS = {'.log', '.txt', '.json', '.csv'}
        from pathlib import Path
        file_ext = Path(file.filename).suffix.lower() if file.filename else ''

        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido. Extensiones válidas: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 3. Sanitizar nombre de archivo (prevenir path traversal)
        safe_filename = Path(file.filename).name if file.filename else 'uploaded_file'
        # Eliminar cualquier carácter peligroso
        import re
        safe_filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', safe_filename)

        # Verificar que el nombre no contenga path traversal
        if '..' in safe_filename or safe_filename.startswith('/'):
            raise HTTPException(
                status_code=400,
                detail="Nombre de archivo inválido"
            )

        logger.info(f"Archivo validado: {safe_filename} ({len(content)} bytes, ext: {file_ext})")
        # ========== FIN VALIDACIONES ==========

        # Verificar si ya hay un archivo procesándose
        if worker_service.current_processing_job:
            raise HTTPException(
                status_code=409,
                detail=f"Ya hay un archivo procesándose: {worker_service.current_processing_job}. Solo se puede procesar un archivo a la vez."
            )
        try:
            file_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # Intentar con latin-1 si falla utf-8 (CSV a veces tiene caracteres especiales)
            file_content = content.decode('latin-1')
            logger.warning(f"Archivo {safe_filename} no es UTF-8, usando latin-1")

        # Calcular hash SHA-256 del contenido para detectar duplicados
        import hashlib
        file_hash = hashlib.sha256(content).hexdigest()

        # Verificar si ya existe un reporte con el mismo hash
        async with db_manager.postgres_pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT id, filename, created_at
                FROM processing.processing_jobs
                WHERE file_hash = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                file_hash
            )

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Este archivo ya fue procesado anteriormente (ID: {existing['id']}, fecha: {existing['created_at']}). Usa el botón 'Re-analizar' en el historial o elimina el reporte anterior primero."
                )

        # Crear chunks y job (pasar file_hash y project_id)
        file_id = await chunk_service.create_chunks_from_file(file_content, safe_filename, file_hash, project_id)
        logger.info(f"✅ Chunks creados para archivo {safe_filename}, file_id: {file_id}")

        # Guardar contenido original del archivo para posible re-análisis
        await db_manager.mongodb_client.logsanomaly.raw_files.insert_one({
            "_id": file_id,
            "filename": safe_filename,
            "content": file_content,
            "size": len(content),
            "upload_date": datetime.utcnow(),
            "file_hash": file_hash
        })
        logger.info(f"✅ Archivo original guardado para re-análisis: {file_id}")
        
        # Iniciar procesamiento en background usando FastAPI BackgroundTasks
        logger.info(f"🚀 Iniciando procesamiento en background para {file_id}")
        background_tasks.add_task(worker_service.process_file_async, file_id)
        logger.info(f"📋 Tarea de procesamiento agregada a background tasks")
        
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
        import traceback
        # Mejorar manejo de errores para HTTPException
        if isinstance(e, HTTPException):
            # Si es HTTPException, relanzarla tal cual
            raise

        error_detail = str(e) if str(e) else type(e).__name__
        logger.error(f"Error procesando archivo: {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {error_detail}"
        )

@app.get("/status/{job_id}", response_model=StatusResponseV2)
async def get_status(job_id: str):
    """Obtener estado de procesamiento"""
    try:
        logger.info(f"Obteniendo estado para job {job_id}")
        async with db_manager.postgres_pool.acquire() as conn:
            job = await conn.fetchrow("""
                SELECT * FROM processing.processing_jobs WHERE id = $1
            """, job_id)

            if not job:
                logger.warning(f"Job {job_id} no encontrado")
                raise HTTPException(status_code=404, detail="Job no encontrado")

            logger.info(f"Job encontrado: status={job['status']}, total_chunks={job['total_chunks']}")

            # Contar chunks procesados
            try:
                chunks_processed = await db_manager.mongodb_client.logsanomaly.chunks.count_documents({
                    "file_id": job_id,
                    "processed": True
                })
                logger.info(f"Chunks procesados: {chunks_processed}")
            except Exception as mongo_error:
                logger.error(f"Error contando chunks en MongoDB: {mongo_error}", exc_info=True)
                chunks_processed = 0

            # Contar anomalías encontradas
            try:
                anomalies_found = await db_manager.mongodb_client.logsanomaly.results.aggregate([
                    {"$match": {"chunk_id": {"$regex": f"^{job_id}"}}},  # chunk_id incluye job_id como prefijo
                    {"$project": {"anomalies": 1, "_id": 0}},
                    {"$unwind": "$anomalies"},
                    {"$count": "total"}
                ]).to_list(length=1)
                anomalies_count = anomalies_found[0]["total"] if anomalies_found else 0
                logger.info(f"Anomalías encontradas: {anomalies_count}")
            except Exception as mongo_error:
                logger.error(f"Error contando anomalías en MongoDB: {mongo_error}", exc_info=True)
                anomalies_count = 0

            # Calcular progreso del chunk actual (para progress bar más visual)
            chunk_progress = 0.0
            if job["status"] == "processing" and chunks_processed < job.get("total_chunks", 1):
                try:
                    # Obtener progreso del chunk actual desde Redis
                    progress_key = f"chunk_progress:{job_id}"
                    progress_data = await db_manager.redis_client.get(progress_key)
                    if progress_data:
                        progress_dict = json.loads(progress_data)
                        chunk_progress = progress_dict.get("progress", 0.0)
                        logger.info(f"Progreso del chunk actual: {chunk_progress:.1f}%")
                    else:
                        chunk_progress = 0.0
                except Exception as redis_error:
                    logger.error(f"Error obteniendo progreso del chunk desde Redis: {redis_error}")
                    chunk_progress = 0.0
            elif job["status"] == "completed":
                chunk_progress = 100.0

            progress = chunks_processed / job["total_chunks"] if job.get("total_chunks", 0) > 0 else 0

            return StatusResponseV2(
                job_id=job_id,
                status=ProcessingStatus(job["status"]),
                progress=progress,
                chunk_progress=chunk_progress,
                chunks_processed=chunks_processed,
                total_chunks=job.get("total_chunks", 0),
                anomalies_found=anomalies_count
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e) if str(e) else "Error interno")

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

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Eliminar un job y todos sus datos asociados (chunks, resultados, vectores)"""
    try:
        from bson import ObjectId

        # Eliminar vectores de Qdrant
        await qdrant_service.delete_job_logs(job_id)
        logger.info(f"Eliminados vectores de Qdrant del job {job_id}")

        # Eliminar chunks de MongoDB
        chunks_result = await db_manager.mongodb_client.logsanomaly.chunks.delete_many({
            "file_id": job_id
        })
        logger.info(f"Eliminados {chunks_result.deleted_count} chunks del job {job_id}")

        # Eliminar resultados de anomalías de MongoDB
        results_result = await db_manager.mongodb_client.logsanomaly.results.delete_many({
            "chunk_id": {"$regex": f"^{job_id}"}
        })
        logger.info(f"Eliminados {results_result.deleted_count} resultados del job {job_id}")

        # Eliminar estadísticas de PostgreSQL
        async with db_manager.postgres_pool.acquire() as conn:
            stats_deleted = await conn.execute("""
                DELETE FROM processing.processing_stats
                WHERE job_id = $1
            """, job_id)
            logger.info(f"Eliminadas estadísticas del job {job_id}")

            # Eliminar job de PostgreSQL
            job_deleted = await conn.execute("""
                DELETE FROM processing.processing_jobs
                WHERE id = $1
            """, job_id)
            logger.info(f"Eliminado job {job_id} de processing_jobs")

        return {
            "message": "Job eliminado correctamente",
            "job_id": job_id,
            "chunks_deleted": chunks_result.deleted_count,
            "results_deleted": results_result.deleted_count
        }

    except Exception as e:
        logger.error(f"Error eliminando job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/reanalyze", response_model=ProcessResponseV2)
async def reanalyze_job(background_tasks: BackgroundTasks, job_id: str):
    """Re-analizar un archivo usando el contenido original guardado"""
    try:
        # Verificar si ya hay un archivo procesándose
        if worker_service.current_processing_job:
            raise HTTPException(
                status_code=409,
                detail=f"Ya hay un archivo procesándose: {worker_service.current_processing_job}. Solo se puede procesar un archivo a la vez."
            )

        # Recuperar el contenido original del archivo
        raw_file = await db_manager.mongodb_client.logsanomaly.raw_files.find_one({"_id": job_id})

        if not raw_file:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el contenido original del archivo {job_id}. El re-análisis no está disponible para este job."
            )

        file_content = raw_file.get("content", "")
        filename = raw_file.get("filename", "unknown")
        original_hash = raw_file.get("file_hash", "")

        # Obtener project_id del job original
        async with db_manager.postgres_pool.acquire() as conn:
            original_job = await conn.fetchrow(
                "SELECT project_id FROM processing.processing_jobs WHERE id = $1",
                job_id
            )
        project_id = original_job["project_id"] if original_job else None

        # Crear chunks y job (esto generará un nuevo file_id)
        new_job_id = await chunk_service.create_chunks_from_file(file_content, filename, original_hash, project_id)
        logger.info(f"✅ Chunks creados para re-análisis {filename}, job_id: {new_job_id}")

        # Guardar contenido original con el nuevo job_id para futuros re-análisis
        await db_manager.mongodb_client.logsanomaly.raw_files.insert_one({
            "_id": new_job_id,
            "filename": filename,
            "content": file_content,
            "size": len(file_content.encode('utf-8')),
            "upload_date": datetime.utcnow(),
            "file_hash": original_hash,
            "reanalyzed_from": job_id  # Referencia al job original
        })
        logger.info(f"✅ Archivo original guardado para re-análisis: {new_job_id} (original: {job_id})")

        # Iniciar procesamiento en background usando FastAPI BackgroundTasks
        logger.info(f"🚀 Iniciando re-procesamiento en background para {new_job_id}")
        background_tasks.add_task(worker_service.process_file_async, new_job_id)
        logger.info(f"📋 Tarea de re-procesamiento agregada a background tasks")

        # Actualizar estado a processing
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute("""
                UPDATE processing.processing_jobs
                SET status = $1, started_at = $2
                WHERE id = $3
            """, ProcessingStatus.PROCESSING, datetime.utcnow(), new_job_id)
        logger.info(f"📊 Estado actualizado a processing para {new_job_id}")

        return ProcessResponseV2(
            job_id=new_job_id,
            status=ProcessingStatus.PROCESSING,
            message=f"Re-análisis iniciado (archivo original: {job_id})",
            total_chunks=len(file_content.split('\n')) // 1000
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else type(e).__name__
        logger.error(f"Error en re-análisis: {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al iniciar el re-análisis: {error_detail}"
        )

@app.get("/jobs/active")
async def get_active_jobs(project_id: str | None = None, current_user = Depends(get_current_user_optional)):
    """
    Obtiene jobs activos (en procesamiento) para el proyecto actual.

    Útil para mostrar procesos en curso cuando la UI se recarga.
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            if project_id:
                jobs = await conn.fetch("""
                    SELECT
                        id,
                        filename,
                        total_size,
                        total_chunks,
                        chunks_processed,
                        status,
                        started_at,
                        project_id
                    FROM processing.processing_jobs
                    WHERE status IN ('pending', 'processing') AND project_id = $1
                    ORDER BY started_at DESC
                """, project_id)
            else:
                jobs = await conn.fetch("""
                    SELECT
                        id,
                        filename,
                        total_size,
                        total_chunks,
                        chunks_processed,
                        status,
                        started_at,
                        project_id
                    FROM processing.processing_jobs
                    WHERE status IN ('pending', 'processing')
                    ORDER BY started_at DESC
                """)

        # Formatear respuesta
        active_jobs = []
        for job in jobs:
            # Calcular progreso estimado
            progress = 0.0
            if job.get("total_chunks", 0) > 0:
                progress = (job.get("chunks_processed", 0) / job["total_chunks"]) * 100

            # Calcular tiempo transcurrido
            from datetime import datetime, timezone
            started_at = job["started_at"]
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

            active_jobs.append({
                "id": str(job["id"]),
                "filename": job["filename"],
                "total_size": job["total_size"],
                "total_chunks": job["total_chunks"],
                "chunks_processed": job.get("chunks_processed", 0),
                "status": job["status"],
                "progress": round(progress, 1),
                "started_at": started_at.isoformat(),
                "elapsed_seconds": int(elapsed),
                "project_id": str(job["project_id"]) if job.get("project_id") else None
            })

        return active_jobs

    except Exception as e:
        logger.error(f"Error obteniendo jobs activos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports")
async def get_reports(project_id: str | None = None):
    """Obtener reportes desde la base de datos, filtrados por project_id si se proporciona"""
    try:
        # Obtener jobs completados, filtrados por project_id si se proporciona
        async with db_manager.postgres_pool.acquire() as conn:
            if project_id:
                jobs = await conn.fetch("""
                    SELECT * FROM processing.processing_jobs
                    WHERE status = 'completed' AND project_id = $1
                    ORDER BY completed_at DESC
                """, project_id)
            else:
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

            # Obtener resultados de anomalías usando job_id como prefijo
            results = await db_manager.mongodb_client.logsanomaly.results.find({
                "chunk_id": {"$regex": f"^{job_id}"}  # chunk_id tiene formato job_id_chunk_id
            }).to_list(length=None)
            
            # Agregar anomalías de todos los chunks
            all_anomalies = []
            for result in results:
                if "anomalies" in result:
                    all_anomalies.extend(result["anomalies"])

            # Agrupar anomalías similares para no mostrar duplicadas
            from services.log_analysis.log_grouper import group_similar_logs

            # Extraer solo los log_entry para agrupación
            anomaly_logs = [anomaly["log_entry"] for anomaly in all_anomalies]

            # Agrupar anomalías similares
            # min_group_size=1 para agrupar TODAS (incluso las únicas aparecen como grupo de 1)
            grouped_anomalies = group_similar_logs(
                anomaly_logs,
                similarity_threshold=0.90,  # 90% de similitud (igual que en evaluación final)
                min_group_size=1  # Agrupar todo, incluyendo únicas
            )

            # Crear lista de anomalías representativas (una por grupo)
            final_anomalies = []

            for pattern, group_data in grouped_anomalies.items():
                # Buscar TODAS las anomalías de este grupo
                group_anomalies = []
                for log in group_data["logs"]:
                    for anomaly in all_anomalies:
                        if anomaly["log_entry"] == log:
                            group_anomalies.append(anomaly)
                            break

                # Priorizar: anomalías con explicación mejorada (tienen "mejorada" o analogías)
                # Luego las que tienen severity asignado
                # Luego cualquier otra
                best_anomaly = None
                best_score = -1

                for anomaly in group_anomalies:
                    score = 0
                    explanation = anomaly.get("explanation", "")

                    # Puntos por explicación mejorada
                    if "mejorada" in explanation.lower() or "imagina" in explanation.lower():
                        score += 100
                    elif "analogía" in explanation.lower() or "restaurante" in explanation.lower():
                        score += 80
                    elif explanation and len(explanation) > 200:
                        score += 50  # Explicaciones largas suelen ser mejores

                    # Puntos por severity
                    if anomaly.get("severity"):
                        score += 20

                    # Puntos si menciona "se repite" o "patrón"
                    if "se repite" in explanation or "patrón" in explanation:
                        score += 30

                    if score > best_score:
                        best_score = score
                        best_anomaly = anomaly

                if best_anomaly:
                    # Modificar la anomalía para incluir información del grupo
                    enhanced_anomaly = best_anomaly.copy()
                    enhanced_anomaly["group_size"] = group_data["count"]
                    enhanced_anomaly["grouped_anomalies"] = group_anomalies
                    final_anomalies.append(enhanced_anomaly)

            # Ordenar por tamaño de grupo (mayor primero) para priorizar anomalías más frecuentes
            final_anomalies.sort(key=lambda x: x.get("group_size", 1), reverse=True)

            # Calcular estadísticas
            total_logs = sum(len(chunk["data"].split('\n')) for chunk in chunks)
            anomalies_detected = len(all_anomalies)  # Total de anomalías detectadas
            chunks_processed = len([chunk for chunk in chunks if chunk.get("processed", False)])
            
            # Crear reporte
            report = {
                "id": str(job_id),
                "timestamp": job["completed_at"].isoformat() if job["completed_at"] else job["started_at"].isoformat(),
                "fileName": job["filename"],
                "total_logs": total_logs,
                "anomalies_detected": anomalies_detected,
                "anomalies": final_anomalies,  # Anomalías agrupadas
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

@app.get("/reports/{job_id}")
async def get_report_by_id(job_id: str):
    """Obtener un reporte específico por su ID

    Este endpoint permite cargar un análisis específico directamente por su ID,
    sin necesidad de especificar el proyecto. Útil para cuando se accede
    directamente a una vista de detalles (ej. al recargar la página).
    """
    try:
        # Buscar el job específico
        async with db_manager.postgres_pool.acquire() as conn:
            job = await conn.fetchrow("""
                SELECT * FROM processing.processing_jobs
                WHERE id = $1 AND status = 'completed'
            """, job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Análisis con ID '{job_id}' no encontrado o no está completado"
            )

        # Obtener chunks del job
        chunks = await db_manager.mongodb_client.logsanomaly.chunks.find({
            "file_id": str(job_id)
        }).to_list(length=None)

        if not chunks:
            logger.warning(f"No se encontraron chunks para el job {job_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Análisis encontrado pero no tiene datos asociados"
            )

        # Obtener resultados de anomalías
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
        total_logs = sum(len(chunk.get("data", "").split('\n')) for chunk in chunks)
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
            "chunks_processed": chunks_processed,
            "project_id": job.get("project_id")  # Incluir project_id para referencia
        }

        logger.info(f"Retornando reporte específico para job_id={job_id}")
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo reporte {job_id} desde BD: {e}")
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
