-- Agregar columna is_dynamic a course_lessons
-- Esta columna indica si una lección se genera dinámicamente

DO $$
BEGIN
    -- Verificar si la columna existe antes de agregarla
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'learning'
        AND table_name = 'course_lessons'
        AND column_name = 'is_dynamic'
    ) THEN
        ALTER TABLE learning.course_lessons
        ADD COLUMN is_dynamic BOOLEAN DEFAULT FALSE;

        RAISE NOTICE 'Columna is_dynamic agregada a learning.course_lessons';
    ELSE
        RAISE NOTICE 'Columna is_dynamic ya existe en learning.course_lessons';
    END IF;
END $$;

-- Crear índice para mejorar performance de consultas de lecciones dinámicas
CREATE INDEX IF NOT EXISTS idx_course_lessons_is_dynamic
ON learning.course_lessons(is_dynamic)
WHERE is_dynamic = TRUE;

COMMENT ON COLUMN learning.course_lessons.is_dynamic IS 'Indica si el contenido de la lección se genera dinámicamente desde anomalías del proyecto';
