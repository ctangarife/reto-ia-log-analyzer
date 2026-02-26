-- ============================================================================
-- Script de Inicialización PostgreSQL - LogsAnomaly
-- ============================================================================
-- Este script crea schemas separados para organizar las tablas:
-- 1. Schema 'processing' - Tablas de procesamiento de logs
-- 2. Schema 'auth' - Sistema de autenticación, autorización y organización (usuarios, workspaces, proyectos, permisos)
-- 3. Schema 'public' - Solo extensiones y funciones compartidas
-- ============================================================================

-- Extensiones necesarias (en schema public)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- CREAR SCHEMAS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS processing;
CREATE SCHEMA IF NOT EXISTS auth;

-- Otorgar permisos al usuario de la aplicación
GRANT USAGE ON SCHEMA processing TO anomaly_user;
GRANT USAGE ON SCHEMA auth TO anomaly_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA processing TO anomaly_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO anomaly_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA processing TO anomaly_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO anomaly_user;

-- Configurar search_path para que el usuario use los schemas por defecto
ALTER USER anomaly_user SET search_path = auth, processing, public;

-- ============================================================================
-- SCHEMA: PROCESSING - Tablas de Procesamiento de Logs
-- ============================================================================

-- Tabla de trabajos de procesamiento
CREATE TABLE IF NOT EXISTS processing.processing_jobs (
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
CREATE TABLE IF NOT EXISTS processing.processing_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES processing.processing_jobs(id),
    chunk_number INTEGER NOT NULL,
    processing_time FLOAT,
    anomalies_found INTEGER DEFAULT 0,
    memory_used BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de configuraciones
CREATE TABLE IF NOT EXISTS processing.configurations (
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
CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing.processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_filename ON processing.processing_jobs(filename);
CREATE INDEX IF NOT EXISTS idx_stats_job_id ON processing.processing_stats(job_id);
CREATE INDEX IF NOT EXISTS idx_config_active ON processing.configurations(is_active);

-- Configuración inicial por defecto
INSERT INTO processing.configurations (
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

-- ============================================================================
-- SCHEMA: AUTH - Sistema de Autenticación, Autorización y Organización
-- ============================================================================
-- Estructura jerárquica: Workspace -> Projects -> Jobs/Anomalies
-- Sistema de permisos basado en módulos y roles

-- ============================================================================
-- TABLAS DE USUARIOS Y AUTENTICACIÓN
-- ============================================================================

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_super_admin BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de sesiones (para JWT tokens)
CREATE TABLE IF NOT EXISTS auth.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- ============================================================================
-- TABLAS DE MÓDULOS Y PERMISOS
-- ============================================================================

-- Tabla de módulos (áreas funcionales del sistema)
CREATE TABLE IF NOT EXISTS auth.modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'logs', 'projects', 'workspaces', 'anomalies', 'reports', 'settings'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de permisos (acciones dentro de módulos)
CREATE TABLE IF NOT EXISTS auth.permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id UUID NOT NULL REFERENCES auth.modules(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,  -- 'read', 'write', 'delete', 'admin'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, action)
);

-- Tabla de roles del sistema
CREATE TABLE IF NOT EXISTS auth.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'super_admin', 'workspace_admin', 'project_admin', 'analyst', 'viewer'
    description TEXT,
    is_system_role BOOLEAN DEFAULT true,  -- Roles del sistema no se pueden eliminar
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de relación: Roles -> Permisos
CREATE TABLE IF NOT EXISTS auth.role_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id UUID NOT NULL REFERENCES auth.roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES auth.permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

-- ============================================================================
-- TABLAS DE WORKSPACES Y PROYECTOS
-- ============================================================================

-- Tabla de workspaces (nivel superior de organización)
CREATE TABLE IF NOT EXISTS auth.workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,  -- URL-friendly identifier
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de proyectos (hijos de workspaces)
CREATE TABLE IF NOT EXISTS auth.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES auth.workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,  -- URL-friendly identifier
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de asignación de roles de usuarios a workspaces
CREATE TABLE IF NOT EXISTS auth.user_workspace_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES auth.workspaces(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES auth.roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, workspace_id, role_id)
);

-- Tabla de asignación de roles de usuarios a proyectos
CREATE TABLE IF NOT EXISTS auth.user_project_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES auth.projects(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES auth.roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, project_id, role_id)
);

-- ============================================================================
-- ÍNDICES PARA AUTH
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON auth.users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON auth.users(is_active);
CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON auth.workspaces(slug);
CREATE INDEX IF NOT EXISTS idx_workspaces_active ON auth.workspaces(is_active);
CREATE INDEX IF NOT EXISTS idx_projects_workspace ON auth.projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_projects_slug ON auth.projects(slug);
CREATE INDEX IF NOT EXISTS idx_projects_active ON auth.projects(is_active);
CREATE INDEX IF NOT EXISTS idx_user_workspace_roles_user ON auth.user_workspace_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_workspace_roles_workspace ON auth.user_workspace_roles(workspace_id);
CREATE INDEX IF NOT EXISTS idx_user_project_roles_user ON auth.user_project_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_project_roles_project ON auth.user_project_roles(project_id);

-- ============================================================================
-- DATOS INICIALES: MÓDULOS
-- ============================================================================

INSERT INTO auth.modules (name, description) VALUES
    ('logs', 'Módulo de procesamiento y análisis de logs'),
    ('projects', 'Módulo de gestión de proyectos'),
    ('workspaces', 'Módulo de gestión de workspaces'),
    ('anomalies', 'Módulo de anomalías detectadas'),
    ('reports', 'Módulo de reportes y análisis'),
    ('settings', 'Módulo de configuración del sistema'),
    ('monitoring', 'Módulo de monitoreo del sistema')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- DATOS INICIALES: PERMISOS
-- ============================================================================

-- Función helper para insertar permisos
DO $$
DECLARE
    mod_logs UUID;
    mod_projects UUID;
    mod_workspaces UUID;
    mod_anomalies UUID;
    mod_reports UUID;
    mod_settings UUID;
    mod_monitoring UUID;
BEGIN
    -- Obtener IDs de módulos
    SELECT id INTO mod_logs FROM auth.modules WHERE name = 'logs';
    SELECT id INTO mod_projects FROM auth.modules WHERE name = 'projects';
    SELECT id INTO mod_workspaces FROM auth.modules WHERE name = 'workspaces';
    SELECT id INTO mod_anomalies FROM auth.modules WHERE name = 'anomalies';
    SELECT id INTO mod_reports FROM auth.modules WHERE name = 'reports';
    SELECT id INTO mod_settings FROM auth.modules WHERE name = 'settings';
    SELECT id INTO mod_monitoring FROM auth.modules WHERE name = 'monitoring';

    -- Permisos para logs
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_logs, 'read', 'Ver logs y resultados de procesamiento'),
        (mod_logs, 'write', 'Subir y procesar logs'),
        (mod_logs, 'delete', 'Eliminar logs y resultados')
    ON CONFLICT (module_id, action) DO NOTHING;

    -- Permisos para projects
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_projects, 'read', 'Ver proyectos'),
        (mod_projects, 'write', 'Crear y editar proyectos'),
        (mod_projects, 'delete', 'Eliminar proyectos'),
        (mod_projects, 'admin', 'Administración completa de proyectos')
    ON CONFLICT (module_id, action) DO NOTHING;

    -- Permisos para workspaces
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_workspaces, 'read', 'Ver workspaces'),
        (mod_workspaces, 'write', 'Crear y editar workspaces'),
        (mod_workspaces, 'delete', 'Eliminar workspaces'),
        (mod_workspaces, 'admin', 'Administración completa de workspaces')
    ON CONFLICT (module_id, action) DO NOTHING;

    -- Permisos para anomalies
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_anomalies, 'read', 'Ver anomalías detectadas'),
        (mod_anomalies, 'write', 'Marcar anomalías, agregar feedback')
    ON CONFLICT (module_id, action) DO NOTHING;

    -- Permisos para reports
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_reports, 'read', 'Ver reportes'),
        (mod_reports, 'write', 'Generar reportes')
    ON CONFLICT (module_id, action) DO NOTHING;

    -- Permisos para settings
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_settings, 'read', 'Ver configuración'),
        (mod_settings, 'write', 'Modificar configuración')
    ON CONFLICT (module_id, action) DO NOTHING;

    -- Permisos para monitoring
    INSERT INTO auth.permissions (module_id, action, description) VALUES
        (mod_monitoring, 'read', 'Ver métricas y monitoreo del sistema')
    ON CONFLICT (module_id, action) DO NOTHING;
END $$;

-- ============================================================================
-- DATOS INICIALES: ROLES DEL SISTEMA
-- ============================================================================

INSERT INTO auth.roles (name, description, is_system_role) VALUES
    ('super_admin', 'Administrador del sistema con acceso completo a todo', true),
    ('workspace_admin', 'Administrador de workspace con acceso completo dentro del workspace', true),
    ('project_admin', 'Administrador de proyecto con acceso completo dentro del proyecto', true),
    ('analyst', 'Analista con permisos de lectura y escritura limitados', true),
    ('viewer', 'Solo lectura, sin permisos de escritura', true)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- ASIGNACIÓN DE PERMISOS A ROLES
-- ============================================================================

-- Función helper para asignar permisos a roles
DO $$
DECLARE
    role_super_admin UUID;
    role_workspace_admin UUID;
    role_project_admin UUID;
    role_analyst UUID;
    role_viewer UUID;
    perm_id UUID;
BEGIN
    -- Obtener IDs de roles
    SELECT id INTO role_super_admin FROM auth.roles WHERE name = 'super_admin';
    SELECT id INTO role_workspace_admin FROM auth.roles WHERE name = 'workspace_admin';
    SELECT id INTO role_project_admin FROM auth.roles WHERE name = 'project_admin';
    SELECT id INTO role_analyst FROM auth.roles WHERE name = 'analyst';
    SELECT id INTO role_viewer FROM auth.roles WHERE name = 'viewer';

    -- SUPER_ADMIN: Todos los permisos de todos los módulos
    FOR perm_id IN SELECT id FROM auth.permissions LOOP
        INSERT INTO auth.role_permissions (role_id, permission_id) 
        VALUES (role_super_admin, perm_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    END LOOP;

    -- WORKSPACE_ADMIN: Todos los permisos excepto settings y monitoring
    FOR perm_id IN 
        SELECT p.id FROM auth.permissions p
        JOIN auth.modules m ON p.module_id = m.id
        WHERE m.name NOT IN ('settings', 'monitoring')
    LOOP
        INSERT INTO auth.role_permissions (role_id, permission_id) 
        VALUES (role_workspace_admin, perm_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    END LOOP;

    -- PROJECT_ADMIN: Permisos de proyecto y logs dentro del proyecto
    FOR perm_id IN 
        SELECT p.id FROM auth.permissions p
        JOIN auth.modules m ON p.module_id = m.id
        WHERE m.name IN ('projects', 'logs', 'anomalies', 'reports')
          AND p.action IN ('read', 'write', 'delete', 'admin')
    LOOP
        INSERT INTO auth.role_permissions (role_id, permission_id) 
        VALUES (role_project_admin, perm_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    END LOOP;

    -- ANALYST: Lectura y escritura limitada
    FOR perm_id IN 
        SELECT p.id FROM auth.permissions p
        JOIN auth.modules m ON p.module_id = m.id
        WHERE p.action IN ('read', 'write')
          AND m.name NOT IN ('settings', 'monitoring')
    LOOP
        INSERT INTO auth.role_permissions (role_id, permission_id) 
        VALUES (role_analyst, perm_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    END LOOP;

    -- VIEWER: Solo lectura
    FOR perm_id IN 
        SELECT p.id FROM auth.permissions p
        WHERE p.action = 'read'
    LOOP
        INSERT INTO auth.role_permissions (role_id, permission_id) 
        VALUES (role_viewer, perm_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    END LOOP;
END $$;

-- ============================================================================
-- FUNCIONES SQL PARA VERIFICACIÓN DE PERMISOS (en schema public para acceso global)
-- ============================================================================

-- Función para verificar si un usuario tiene un permiso en un proyecto
CREATE OR REPLACE FUNCTION user_has_project_permission(
    p_user_id UUID,
    p_project_id UUID,
    p_module VARCHAR,
    p_action VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_super_admin BOOLEAN;
    v_workspace_id UUID;
BEGIN
    -- Verificar si es super admin
    SELECT is_super_admin INTO v_is_super_admin
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_is_super_admin THEN
        RETURN true;
    END IF;
    
    -- Obtener workspace_id del proyecto
    SELECT workspace_id INTO v_workspace_id
    FROM auth.projects
    WHERE id = p_project_id;
    
    -- Verificar permiso directo en proyecto
    IF EXISTS (
        SELECT 1
        FROM auth.user_project_roles upr
        JOIN auth.role_permissions rp ON upr.role_id = rp.role_id
        JOIN auth.permissions p ON rp.permission_id = p.id
        JOIN auth.modules m ON p.module_id = m.id
        WHERE upr.user_id = p_user_id
          AND upr.project_id = p_project_id
          AND m.name = p_module
          AND p.action = p_action
    ) THEN
        RETURN true;
    END IF;
    
    -- Verificar permiso heredado del workspace
    IF EXISTS (
        SELECT 1
        FROM auth.user_workspace_roles uwr
        JOIN auth.role_permissions rp ON uwr.role_id = rp.role_id
        JOIN auth.permissions p ON rp.permission_id = p.id
        JOIN auth.modules m ON p.module_id = m.id
        WHERE uwr.user_id = p_user_id
          AND uwr.workspace_id = v_workspace_id
          AND m.name = p_module
          AND p.action = p_action
    ) THEN
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Función para verificar si un usuario tiene un permiso en un workspace
CREATE OR REPLACE FUNCTION user_has_workspace_permission(
    p_user_id UUID,
    p_workspace_id UUID,
    p_module VARCHAR,
    p_action VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_super_admin BOOLEAN;
BEGIN
    -- Verificar si es super admin
    SELECT is_super_admin INTO v_is_super_admin
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_is_super_admin THEN
        RETURN true;
    END IF;
    
    -- Verificar permiso en workspace
    IF EXISTS (
        SELECT 1
        FROM auth.user_workspace_roles uwr
        JOIN auth.role_permissions rp ON uwr.role_id = rp.role_id
        JOIN auth.permissions p ON rp.permission_id = p.id
        JOIN auth.modules m ON p.module_id = m.id
        WHERE uwr.user_id = p_user_id
          AND uwr.workspace_id = p_workspace_id
          AND m.name = p_module
          AND p.action = p_action
    ) THEN
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener workspaces a los que un usuario tiene acceso
CREATE OR REPLACE FUNCTION user_accessible_workspaces(p_user_id UUID)
RETURNS TABLE(workspace_id UUID, workspace_name VARCHAR, role_name VARCHAR) AS $$
BEGIN
    -- Super admin ve todos los workspaces
    IF EXISTS (SELECT 1 FROM auth.users WHERE id = p_user_id AND is_super_admin = true) THEN
        RETURN QUERY
        SELECT w.id, w.name, 'super_admin'::VARCHAR
        FROM auth.workspaces w
        WHERE w.is_active = true;
    ELSE
        -- Usuario normal ve solo workspaces donde tiene rol asignado
        RETURN QUERY
        SELECT DISTINCT w.id, w.name, r.name
        FROM auth.workspaces w
        JOIN auth.user_workspace_roles uwr ON w.id = uwr.workspace_id
        JOIN auth.roles r ON uwr.role_id = r.id
        WHERE uwr.user_id = p_user_id
          AND w.is_active = true;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener proyectos a los que un usuario tiene acceso
CREATE OR REPLACE FUNCTION user_accessible_projects(p_user_id UUID, p_workspace_id UUID DEFAULT NULL)
RETURNS TABLE(project_id UUID, project_name VARCHAR, workspace_id UUID, role_name VARCHAR) AS $$
BEGIN
    -- Super admin ve todos los proyectos
    IF EXISTS (SELECT 1 FROM auth.users WHERE id = p_user_id AND is_super_admin = true) THEN
        RETURN QUERY
        SELECT p.id, p.name, p.workspace_id, 'super_admin'::VARCHAR
        FROM auth.projects p
        JOIN auth.workspaces w ON p.workspace_id = w.id
        WHERE p.is_active = true
          AND w.is_active = true
          AND (p_workspace_id IS NULL OR p.workspace_id = p_workspace_id);
    ELSE
        -- Proyectos donde tiene rol directo
        RETURN QUERY
        SELECT DISTINCT p.id, p.name, p.workspace_id, r.name
        FROM auth.projects p
        JOIN auth.user_project_roles upr ON p.id = upr.project_id
        JOIN auth.roles r ON upr.role_id = r.id
        JOIN auth.workspaces w ON p.workspace_id = w.id
        WHERE upr.user_id = p_user_id
          AND p.is_active = true
          AND w.is_active = true
          AND (p_workspace_id IS NULL OR p.workspace_id = p_workspace_id)
        
        UNION
        
        -- Proyectos donde hereda permisos del workspace
        SELECT DISTINCT p.id, p.name, p.workspace_id, r.name
        FROM auth.projects p
        JOIN auth.workspaces w ON p.workspace_id = w.id
        JOIN auth.user_workspace_roles uwr ON w.id = uwr.workspace_id
        JOIN auth.roles r ON uwr.role_id = r.id
        WHERE uwr.user_id = p_user_id
          AND p.is_active = true
          AND w.is_active = true
          AND (p_workspace_id IS NULL OR p.workspace_id = p_workspace_id)
          AND NOT EXISTS (
              SELECT 1 FROM auth.user_project_roles upr2 
              WHERE upr2.user_id = p_user_id AND upr2.project_id = p.id
          );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMENTARIOS EN TABLAS (Documentación)
-- ============================================================================

COMMENT ON SCHEMA processing IS 'Schema para tablas de procesamiento de logs y análisis de anomalías';
COMMENT ON SCHEMA auth IS 'Schema para sistema de autenticación, autorización y organización (usuarios, workspaces, proyectos, permisos)';

COMMENT ON TABLE auth.workspaces IS 'Espacios de trabajo de nivel superior. Contienen proyectos.';
COMMENT ON TABLE auth.projects IS 'Proyectos que pertenecen a un workspace. Contienen jobs de procesamiento y anomalías.';
COMMENT ON TABLE auth.user_workspace_roles IS 'Asignación de roles de usuarios a workspaces';
COMMENT ON TABLE auth.user_project_roles IS 'Asignación de roles de usuarios a proyectos (hereda permisos del workspace si no tiene rol directo)';
COMMENT ON TABLE auth.modules IS 'Módulos funcionales del sistema (logs, projects, workspaces, anomalies, reports, settings, monitoring)';
COMMENT ON TABLE auth.permissions IS 'Permisos específicos dentro de cada módulo (read, write, delete, admin)';
COMMENT ON TABLE auth.roles IS 'Roles del sistema que agrupan permisos';

-- ============================================================================
-- FIN DEL SCRIPT DE INICIALIZACIÓN
-- ============================================================================
