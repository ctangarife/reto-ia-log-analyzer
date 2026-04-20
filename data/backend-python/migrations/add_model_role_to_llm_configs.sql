-- ============================================================================
-- Migración: Agregar campo model_role para selección de modelos LLM
-- Fecha: 2026-04-19
-- Descripción: Soporte para modelos default, fallback y evaluadores
-- ============================================================================

-- 1. Agregar campo model_role (default 'default' para compatibilidad con registros existentes)
ALTER TABLE auth.workspace_llm_configs
ADD COLUMN IF NOT EXISTS model_role VARCHAR(20) DEFAULT 'default' NOT NULL;

-- 2. Actualizar registros existentes a model_role='default'
UPDATE auth.workspace_llm_configs
SET model_role = 'default'
WHERE model_role IS NULL OR model_role = '';

-- 3. Eliminar la restricción UNIQUE anterior (workspace_id, provider)
ALTER TABLE auth.workspace_llm_configs
DROP CONSTRAINT IF EXISTS uq_workspace_llm_configs;

-- 4. Crear nueva restricción UNIQUE incluyendo model_role
ALTER TABLE auth.workspace_llm_configs
ADD CONSTRAINT uq_workspace_llm_configs_role
UNIQUE (workspace_id, provider, model_role);

-- 5. Crear índice para búsquedas por rol (útil para obtener fallbacks/evaluators)
CREATE INDEX IF NOT EXISTS idx_workspace_llm_configs_role
ON auth.workspace_llm_configs (workspace_id, model_role);

-- 6. Agregar restricción de check para validar valores de model_role
ALTER TABLE auth.workspace_llm_configs
ADD CONSTRAINT chk_model_role
CHECK (model_role IN ('default', 'fallback', 'evaluator'));

-- 7. Comentarios para documentar
COMMENT ON COLUMN auth.workspace_llm_configs.model_role IS 'Role del modelo: default (principal), fallback (respaldo), evaluator (evaluador)';
COMMENT ON CONSTRAINT chk_model_role ON auth.workspace_llm_configs IS 'Valores permitidos: default, fallback, evaluator';
