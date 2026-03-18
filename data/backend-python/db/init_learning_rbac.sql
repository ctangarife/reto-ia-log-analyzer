-- Learning/Course RBAC Setup
-- Integrates the course system with the existing RBAC structure

-- 1. Create the learning module
INSERT INTO auth.modules (id, name, description)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'learning',
    'Módulo de cursos interactivos y aprendizaje'
)
ON CONFLICT (id) DO NOTHING;

-- 2. Create learning permissions
-- Course creation and management
INSERT INTO auth.permissions (id, module_id, action, description) VALUES
    ('00000000-0000-0000-0001-000000000001', '00000000-0000-0000-0000-000000000001', 'create', 'Crear nuevos cursos desde anomalías del proyecto'),
    ('00000000-0000-0000-0001-000000000002', '00000000-0000-0000-0000-000000000001', 'edit', 'Editar cualquier curso del workspace'),
    ('00000000-0000-0000-0001-000000000003', '00000000-0000-0000-0000-000000000001', 'edit_own', 'Editar solo cursos propios'),
    ('00000000-0000-0000-0001-000000000004', '00000000-0000-0000-0000-000000000001', 'edit_lessons', 'Editar contenido de lecciones'),
    ('00000000-0000-0000-0001-000000000005', '00000000-0000-0000-0000-000000000001', 'minor_edit', 'Hacer correcciones menores sin aprobación'),
    -- Course review and approval
    ('00000000-0000-0000-0001-000000000006', '00000000-0000-0000-0000-000000000001', 'review', 'Revisar y aprobar/rechazar cursos'),
    ('00000000-0000-0000-0001-000000000007', '00000000-0000-0000-0000-000000000001', 'delete', 'Eliminar o archivar cursos'),
    ('00000000-0000-0000-0001-000000000008', '00000000-0000-0000-0000-000000000001', 'publish', 'Publicar cursos sin aprobación previa'),
    -- Course viewing
    ('00000000-0000-0000-0001-000000000009', '00000000-0000-0000-0000-000000000001', 'view_draft', 'Ver cursos en borrador'),
    ('00000000-0000-0000-0001-000000000010', '00000000-0000-0000-0000-000000000001', 'view_pending', 'Ver cursos pendientes de revisión')
ON CONFLICT DO NOTHING;

-- 3. Create course-specific roles
INSERT INTO auth.roles (id, name, description, is_system_role) VALUES
    (
        '00000000-0000-0000-0002-000000000001',
        'course_creator',
        'Puede crear y editar sus propios cursos interactivos',
        false
    ),
    (
        '00000000-0000-0000-0002-000000000002',
        'course_reviewer',
        'Puede revisar cursos y aprobarlos/rechazarlos',
        false
    ),
    (
        '00000000-0000-0000-0002-000000000003',
        'course_admin',
        'Control total sobre cursos (crear, editar, revisar, publicar)',
        false
    )
ON CONFLICT (id) DO NOTHING;

-- 4. Assign permissions to roles

-- course_creator permissions: create, edit_own, edit_lessons, minor_edit, view_draft
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0002-000000000001', id
FROM auth.permissions
WHERE module_id = '00000000-0000-0000-0000-000000000001'
AND action IN ('create', 'edit_own', 'edit_lessons', 'minor_edit', 'view_draft')
ON CONFLICT DO NOTHING;

-- course_reviewer permissions: review, view_pending, view_draft, minor_edit
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0002-000000000002', id
FROM auth.permissions
WHERE module_id = '00000000-0000-0000-0000-000000000001'
AND action IN ('review', 'view_pending', 'view_draft', 'minor_edit')
ON CONFLICT DO NOTHING;

-- course_admin permissions: ALL learning permissions
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0002-000000000003', id
FROM auth.permissions
WHERE module_id = '00000000-0000-0000-0000-000000000001'
ON CONFLICT DO NOTHING;

-- 5. Grant course_admin role to super_admin by default
INSERT INTO auth.user_workspace_roles (user_id, workspace_id, role_id)
SELECT u.id, w.id, '00000000-0000-0000-0002-000000000003'
FROM auth.users u
CROSS JOIN auth.workspaces w
WHERE u.is_super_admin = true
ON CONFLICT DO NOTHING;
