-- ============================================================================
-- Migración v2: Nueva tabla 'courses' separada de 'course_modules'
-- ============================================================================
-- Esta migración crea una nueva estructura donde:
-- - courses: Entidad principal del curso (estado, versión, etc.)
-- - course_modules: Hijos de courses (módulos del curso)
-- - course_lessons: Hijos de course_modules (lecciones del módulo)
--
-- Estructura del curso: 1 curso -> 4 módulos -> N lecciones
-- ============================================================================

-- 1. Crear la nueva tabla 'courses'
CREATE TABLE IF NOT EXISTS learning.courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    -- Flujo de trabajo
    status VARCHAR(20) DEFAULT 'draft',  -- draft, pending, approved, published, archived
    scope VARCHAR(20) DEFAULT 'project',  -- project, workspace
    version_number INT DEFAULT 1,
    -- Creación y revisión
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    published_at TIMESTAMP,
    archived_at TIMESTAMP,
    rejection_reason TEXT,
    change_description TEXT
);

-- 2. Modificar course_modules para que tengan course_id en lugar de parent_id
-- Primero, creamos una nueva columna course_id
ALTER TABLE learning.course_modules ADD COLUMN IF NOT EXISTS course_id UUID;

-- 3. Crear índices para la nueva estructura
CREATE INDEX IF NOT EXISTS idx_courses_project ON learning.courses(project_id, status);
CREATE INDEX IF NOT EXISTS idx_courses_workspace ON learning.courses(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_course_modules_course ON learning.course_modules(course_id);

-- 4. Crear función para validar límites de cursos por proyecto
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
    -- Contar cursos por estado
    SELECT COUNT(*) INTO published_count
    FROM learning.courses
    WHERE project_id = p_project_id
    AND status = 'published';

    SELECT COUNT(*) INTO draft_count
    FROM learning.courses
    WHERE project_id = p_project_id
    AND status = 'draft';

    SELECT COUNT(*) INTO pending_count
    FROM learning.courses
    WHERE project_id = p_project_id
    AND status = 'pending';

    -- Validar límites
    IF p_status = 'published' AND published_count >= 1 THEN
        RETURN QUERY SELECT FALSE, 'Ya existe un curso publicado para este proyecto', jsonb_build_object(
            'published', published_count,
            'draft', draft_count,
            'pending', pending_count
        );
    ELSIF p_status = 'draft' AND draft_count >= 3 THEN
        RETURN QUERY SELECT FALSE, 'Máximo de 3 cursos en borrador alcanzado', jsonb_build_object(
            'published', published_count,
            'draft', draft_count,
            'pending', pending_count
        );
    ELSIF p_status = 'pending' AND pending_count >= 3 THEN
        RETURN QUERY SELECT FALSE, 'Máximo de 3 cursos pendientes alcanzado', jsonb_build_object(
            'published', published_count,
            'draft', draft_count,
            'pending', pending_count
        );
    ELSE
        RETURN QUERY SELECT TRUE, 'Límites válidos', jsonb_build_object(
            'published', published_count,
            'draft', draft_count,
            'pending', pending_count
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 5. Comentar las tablas
COMMENT ON TABLE learning.courses IS 'Cursos principales - cada curso pertenece a un proyecto y contiene 4 módulos';
COMMENT ON TABLE learning.course_modules IS 'Módulos de un curso - un curso tiene 4 módulos fijos';
COMMENT ON FUNCTION learning.validate_course_modules IS 'Valida los límites de cursos por proyecto: máx 1 published, 3 draft, 3 pending';

-- 6. Otorgar permisos
GRANT ALL PRIVILEGES ON TABLE learning.courses TO anomaly_user;
GRANT EXECUTE ON FUNCTION learning.validate_course_limits TO anomaly_user;
