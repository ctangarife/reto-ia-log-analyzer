# API REST de Proyectos

**Endpoints base**:  
- Listado y creación bajo workspace: `/api/workspaces/{workspace_id}/projects`  
- Obtener/actualizar/desactivar por ID: `/api/projects/{project_id}`  

El prefijo `/api` lo añade el proxy nginx.

**Última actualización**: 2026-02-03

---

## Autenticación

Todos los endpoints requieren JWT:

```
Authorization: Bearer <token>
```

---

## Endpoints bajo workspace

### 1. Listar proyectos de un workspace

**GET** `/api/workspaces/{workspace_id}/projects`

**Descripción**: Devuelve los proyectos a los que el usuario tiene acceso dentro del workspace. El usuario debe tener acceso al workspace. Super admin ve todos los proyectos activos del workspace; el resto solo los que tienen rol (directo o heredado).

**Permisos**: Usuario con acceso al workspace.

**Response** (200 OK):

```json
[
  {
    "id": "uuid-project",
    "project_id": "uuid-project",
    "workspace_id": "uuid-workspace",
    "name": "Análisis de logs de producción",
    "slug": "analisis-logs-produccion",
    "description": "Proyecto principal",
    "is_active": true,
    "role": "project_admin",
    "created_at": "2026-02-03T12:00:00",
    "updated_at": "2026-02-03T12:00:00"
  }
]
```

**Errores**:
- `404 Not Found`: Workspace no encontrado o sin acceso
- `500 Internal Server Error`: Error al listar proyectos

---

### 2. Crear proyecto en un workspace

**POST** `/api/workspaces/{workspace_id}/projects`

**Descripción**: Crea un proyecto dentro del workspace. Requiere permiso `projects:write` o `projects:admin` en el workspace, o ser super administrador.

**Permisos**: Acceso al workspace + permiso write/admin o super admin.

**Request Body**:

```json
{
  "name": "Mi Proyecto",
  "description": "Descripción opcional",
  "slug": "mi-proyecto",
  "workspace_id": "uuid-workspace"
}
```

- `name` (string, requerido): Nombre del proyecto (1–255 caracteres).
- `description` (string, opcional): Descripción.
- `slug` (string, opcional): Identificador URL-friendly único en todo el sistema; si no se envía, se genera desde `name`.
- `workspace_id` en el body puede enviarse por compatibilidad; se usa el `workspace_id` de la URL.

**Response** (201 Created):

```json
{
  "id": "uuid-project",
  "project_id": "uuid-project",
  "workspace_id": "uuid-workspace",
  "name": "Mi Proyecto",
  "slug": "mi-proyecto",
  "description": "Descripción opcional",
  "is_active": true,
  "created_by": "uuid-usuario",
  "created_at": "2026-02-03T12:00:00",
  "updated_at": "2026-02-03T12:00:00"
}
```

**Errores**:
- `403 Forbidden`: Sin permiso para crear proyectos en este workspace
- `404 Not Found`: Workspace no encontrado o sin acceso
- `500 Internal Server Error`: Error al crear el proyecto

---

## Endpoints por ID de proyecto

### 3. Obtener un proyecto

**GET** `/api/projects/{project_id}`

**Descripción**: Devuelve un proyecto por ID. El usuario debe tener acceso al proyecto.

**Permisos**: Usuario con acceso al proyecto.

**Response** (200 OK): Mismo formato que un item de la lista (sin `role`), con `created_by` si aplica.

**Errores**:
- `404 Not Found`: Proyecto no encontrado o sin acceso

---

### 4. Actualizar proyecto

**PUT** `/api/projects/{project_id}`

**Descripción**: Actualiza nombre, descripción o estado activo. Requiere permiso `projects:write` o `projects:admin` en el proyecto, o ser super administrador.

**Permisos**: Acceso al proyecto + permiso write/admin o super admin.

**Request Body** (todos opcionales):

```json
{
  "name": "Nuevo nombre",
  "description": "Nueva descripción",
  "is_active": true
}
```

**Response** (200 OK): Objeto proyecto actualizado.

**Errores**:
- `403 Forbidden`: Sin permiso para editar
- `404 Not Found`: Proyecto no encontrado o sin acceso

---

### 5. Desactivar proyecto

**DELETE** `/api/projects/{project_id}`

**Descripción**: Desactiva el proyecto (soft delete: `is_active = false`). Requiere permiso `projects:delete` o `projects:admin` en el proyecto, o ser super administrador.

**Permisos**: Acceso al proyecto + permiso delete/admin o super admin.

**Response** (200 OK):

```json
{
  "message": "Proyecto desactivado",
  "project_id": "uuid-project"
}
```

**Errores**:
- `403 Forbidden`: Sin permiso para eliminar
- `404 Not Found`: Proyecto no encontrado o sin acceso

---

## Resumen de permisos

| Acción | Condición |
|--------|-----------|
| Listar proyectos de un workspace | Acceso al workspace |
| Crear proyecto en workspace | Acceso al workspace + `projects:write` o `projects:admin` o super admin |
| Ver un proyecto | Acceso al proyecto |
| Editar proyecto | Acceso + `projects:write` o `projects:admin` o super admin |
| Desactivar proyecto | Acceso + `projects:delete` o `projects:admin` o super admin |

---

## Servicios y rutas en el backend

- **Servicio**: `data/backend-python/services/project_service.py`
- **Rutas de listado/creación**: `data/backend-python/routes/workspaces.py` (GET/POST `/{workspace_id}/projects`)
- **Rutas por ID**: `data/backend-python/routes/projects.py` (prefijo `/projects`)
- **Modelos**: `models/rbac_models.py` (`ProjectCreate`, `ProjectUpdate`)
