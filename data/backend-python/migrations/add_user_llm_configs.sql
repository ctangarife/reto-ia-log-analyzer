-- ============================================================================
-- Migración: Agregar configuración LLM de workspaces
-- Fecha: 2026-04-19
-- Descripción: Crea tabla para almacenar credenciales LLM a nivel workspace
-- ============================================================================

-- Crear tabla de configuraciones LLM de workspaces
CREATE TABLE IF NOT EXISTS auth.workspace_llm_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES auth.workspaces(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    api_key TEXT,  -- Encriptado
    api_endpoint TEXT,
    model VARCHAR(100),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_workspace_llm_configs UNIQUE (workspace_id, provider)
);

-- Crear índices
CREATE INDEX IF NOT EXISTS idx_workspace_llm_configs_workspace ON auth.workspace_llm_configs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_llm_configs_provider ON auth.workspace_llm_configs(provider);

-- Crear trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION auth.update_workspace_llm_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_workspace_llm_configs_updated_at
    BEFORE UPDATE ON auth.workspace_llm_configs
    FOR EACH ROW
    EXECUTE FUNCTION auth.update_workspace_llm_configs_updated_at();

-- Comentarios
COMMENT ON TABLE auth.workspace_llm_configs IS 'Configuraciones LLM de workspaces (API keys encriptadas)';
COMMENT ON COLUMN auth.workspace_llm_configs.api_key IS 'API key encriptada del proveedor LLM';
COMMENT ON COLUMN auth.workspace_llm_configs.is_default IS 'Marca esta configuración como la default del workspace';
