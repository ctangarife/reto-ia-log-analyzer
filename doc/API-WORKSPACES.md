# API REST de Workspaces

**Endpoint base**: `/api/workspaces` (el prefijo `/api` lo añade el proxy nginx; en el backend las rutas son `/workspaces`).

**Última actualización**: 2026-02-03

---

## Autenticación

Todos los endpoints requieren autenticación JWT:

```
Authorization: Bearer <token>
```

---

## Endpoints

### 1. Listar workspaces

**GET** `/api/workspaces`

**Descripción**: Devuelve los workspaces a los que el usuario tiene acceso. Un super admin ve todos los workspaces activos; el resto solo los que tienen un rol asignado.

**Permisos**: Usuario autenticado.

**Response** (200 OK):

```json
[
  {
    "id": "uuid-workspace",
    "workspace_id": "uuid-workspace",
    "name": "Departamento de IT",
    "slug": "departamento-de-it",
    "description": "Workspace principal",
    "is_active": true,
    "role": "workspace_admin",
    "created_at": "2026-02-01T12:00:00",
    "updated_at": "2026-02-01T12:00:00"
  }
]
```

**Errores**:
- `401 Unauthorized`: Token ausente o inválido

---

### 2. Crear workspace

**POST** `/api/workspaces`

**Descripción**: Crea un nuevo workspace. Solo super administrador.

**Permisos**: Super administrador.

**Request Body**:

```json
{
  "name": "Mi Workspace",
  "description": "Descripción opcional",
  "slug": "mi-workspace"
}
```

- `name` (string, requerido): Nombre del workspace (1–255 caracteres).
- `description` (string, opcional): Descripción.
- `slug` (string, opcional): Identificador URL-friendly; si no se envía, se genera a partir de `name` (único).

**Response** (201 Created):

```json
{
  "id": "uuid-workspace",
  "workspace_id": "uuid-workspace",
  "name": "Mi Workspace",
  "slug": "mi-workspace",
  "description": "Descripción opcional",
  "is_active": true,
  "created_by": "uuid-usuario",
  "created_at": "2026-02-03T12:00:00",
  "updated_at": "2026-02-03T12:00:00"
}
```

**Errores**:
- `403 Forbidden`: No eres super administrador
- `500 Internal Server Error`: Error al crear el workspace

---

### 3. Obtener un workspace

**GET** `/api/workspaces/{workspace_id}`

**Descripción**: Devuelve un workspace por ID. El usuario debe tener acceso (rol en el workspace o super admin).

**Permisos**: Usuario con acceso al workspace.

**Response** (200 OK):

```json
{
  "id": "uuid-workspace",
  "workspace_id": "uuid-workspace",
  "name": "Mi Workspace",
  "slug": "mi-workspace",
  "description": "Descripción",
  "is_active": true,
  "created_by": "uuid-usuario",
  "created_at": "2026-02-03T12:00:00",
  "updated_at": "2026-02-03T12:00:00"
}
```

**Errores**:
- `404 Not Found`: Workspace no encontrado o sin acceso

---

### 4. Actualizar workspace

**PUT** `/api/workspaces/{workspace_id}`

**Descripción**: Actualiza nombre, descripción o estado activo. Requiere permiso `workspaces:write` o `workspaces:admin` en el workspace, o ser super administrador.

**Permisos**: Acceso al workspace + permiso de escritura/admin o super admin.

**Request Body** (todos los campos opcionales):

```json
{
  "name": "Nuevo nombre",
  "description": "Nueva descripción",
  "is_active": true
}
```

**Response** (200 OK): Mismo formato que “Obtener un workspace”.

**Errores**:
- `403 Forbidden`: Sin permiso para editar
- `404 Not Found`: Workspace no encontrado o sin acceso

---

### 5. Desactivar workspace

**DELETE** `/api/workspaces/{workspace_id}`

**Descripción**: Desactiva el workspace (soft delete: `is_active = false`). Requiere permiso `workspaces:delete` o `workspaces:admin` en el workspace, o ser super administrador.

**Permisos**: Acceso al workspace + permiso delete/admin o super admin.

**Response** (200 OK):

```json
{
  "message": "Workspace desactivado",
  "workspace_id": "uuid-workspace"
}
```

**Errores**:
- `403 Forbidden`: Sin permiso para eliminar
- `404 Not Found`: Workspace no encontrado o sin acceso

---

## Resumen de permisos

| Acción              | Condición                                                                 |
|---------------------|---------------------------------------------------------------------------|
| Listar workspaces   | Usuario autenticado (solo ve los que tienen rol o super admin todos)     |
| Crear workspace     | Super administrador                                                      |
| Ver un workspace   | Tener acceso al workspace (rol o super admin)                             |
| Editar workspace   | Acceso + permiso `workspaces:write` o `workspaces:admin` o super admin     |
| Desactivar         | Acceso + permiso `workspaces:delete` o `workspaces:admin` o super admin    |

---

## Servicio y rutas en el backend

- **Servicio**: `data/backend-python/services/workspace_service.py`
- **Rutas**: `data/backend-python/routes/workspaces.py` (prefijo `/workspaces`)
- **Modelos**: `models/rbac_models.py` (`WorkspaceCreate`, `WorkspaceUpdate`)
