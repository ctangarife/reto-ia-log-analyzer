# Implementación Frontend: Endpoints de Workspaces

> **Documento para el agente de UI**  
> Cómo integrar en el frontend los nuevos endpoints REST de workspaces del backend.  
> Complementa la [Guía para Desarrolladores Frontend](../GUIA-DESARROLLADOR-FRONTEND.md).

**Última actualización**: 2026-02-03

---

## 📋 Tabla de Contenidos

1. [Contexto y Base URL](#contexto-y-base-url)
2. [Tipos e Interfaces](#tipos-e-interfaces)
3. [GET /api/workspaces – Listar workspaces](#get-apiworkspaces--listar-workspaces)
4. [POST /api/workspaces – Crear workspace](#post-apiworkspaces--crear-workspace)
5. [GET /api/workspaces/{id} – Obtener un workspace](#get-apiworkspacesid--obtener-un-workspace)
6. [PUT /api/workspaces/{id} – Actualizar workspace](#put-apiworkspacesid--actualizar-workspace)
7. [DELETE /api/workspaces/{id} – Desactivar workspace](#delete-apiworkspacesid--desactivar-workspace)
8. [Integración con RBAC y flujo de la app](#integración-con-rbac-y-flujo-de-la-app)
9. [Checklist de implementación](#checklist-de-implementación)

---

## Contexto y Base URL

- **Base URL**: Todas las peticiones desde el frontend usan `/api/*`. Nginx reescribe al backend (ver [GUIA-DESARROLLADOR-FRONTEND.md](../GUIA-DESARROLLADOR-FRONTEND.md)).
- **Autenticación**: Todos los endpoints de workspaces requieren JWT:
  ```
  Authorization: Bearer <jwt_token>
  ```
- **Relación con RBAC**: Los workspaces son el nivel superior de la jerarquía (Workspace → Project → Jobs). La lista de workspaces ya viene filtrada por el backend según el usuario; el frontend solo consume y muestra.

---

## Tipos e Interfaces

Definir en el frontend (TypeScript) tipos alineados con la API:

```typescript
// Workspace tal como lo devuelve GET /api/workspaces (lista) o GET/PUT /api/workspaces/{id}
export interface Workspace {
  id: string;
  workspace_id: string;   // mismo que id, por compatibilidad
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  role?: string;          // solo en lista: rol del usuario en este workspace
  created_at: string | null;
  updated_at: string | null;
  created_by?: string | null;  // solo en detalle/creación
}

// Body para crear workspace (POST)
export interface WorkspaceCreate {
  name: string;
  description?: string | null;
  slug?: string | null;
}

// Body para actualizar workspace (PUT); todos opcionales
export interface WorkspaceUpdate {
  name?: string;
  description?: string | null;
  is_active?: boolean;
}
```

- Usar `id` o `workspace_id` de forma consistente (la API devuelve ambos con el mismo valor).
- Las fechas vienen en ISO 8601 (ej. `"2026-02-03T12:00:00"`).

---

## GET `/api/workspaces` – Listar workspaces

**Propósito**: Obtener todos los workspaces a los que el usuario tiene acceso. Base para selector de workspace y navegación.

**Permiso**: Cualquier usuario autenticado. El backend filtra: super admin ve todos los activos; el resto solo los que tienen rol asignado.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Respuesta exitosa (200)**:
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

- Array vacío `[]` si no hay workspaces accesibles.

**Implementación Frontend**:

1. **Servicio/API**: Crear función que llame a `GET /api/workspaces` con el header `Authorization`.
2. **Store**: Guardar la lista en el store de la aplicación (ej. `workspaces: Workspace[]` o en el store de auth/contexto).
3. **Momento de carga**: Llamar tras el login (o al cargar la app si ya hay token), como indica la guía en “Al Cargar la Aplicación” / “Cargar workspaces accesibles”.
4. **Uso en UI**:
   - Selector de workspace (dropdown o lista) para elegir contexto.
   - Navegación lateral o breadcrumb: “Workspace > Proyecto”.
   - Mostrar solo workspaces con `is_active === true` si se desea (el backend ya filtra activos en lista).
5. **Rol**: El campo `role` puede usarse para mostrar badge o para decidir si mostrar acciones “Editar”/“Desactivar” (combinado con permisos cuando existan endpoints de permisos por proyecto/workspace).

**Errores**:
- `401 Unauthorized`: Token ausente o inválido → redirigir al login.
- `500`: Mostrar mensaje genérico y opción de reintentar.

---

## POST `/api/workspaces` – Crear workspace

**Propósito**: Crear un nuevo workspace. Solo super administrador.

**Permiso**: Usuario con `is_super_admin === true`.

**Headers**:
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Body**:
```json
{
  "name": "Mi Workspace",
  "description": "Descripción opcional",
  "slug": "mi-workspace"
}
```
- `name`: obligatorio (1–255 caracteres).
- `description`: opcional.
- `slug`: opcional; si no se envía, el backend lo genera desde `name` (único).

**Respuesta exitosa (201 Created)**:
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

**Implementación Frontend**:

1. **Visibilidad**: Mostrar botón/modal “Crear workspace” solo si el usuario es super admin (usar `is_super_admin` del token o del `/api/auth/me`).
2. **Formulario**: Campos `name` (requerido), `description` (opcional), `slug` (opcional). Validar longitud de `name`.
3. **Envío**: `POST /api/workspaces` con body `WorkspaceCreate`.
4. **Tras éxito**: Añadir el workspace devuelto al store y actualizar el selector; opcionalmente seleccionar el nuevo workspace y cerrar el modal.
5. **Errores**:
   - `403 Forbidden`: No eres super admin → ocultar acción o mostrar “Sin permisos”.
   - `500`: Mensaje “Error al crear el workspace” y opción de reintentar.

---

## GET `/api/workspaces/{id}` – Obtener un workspace

**Propósito**: Obtener detalle de un workspace por ID (para vista de detalle o antes de editar).

**Permiso**: Usuario con acceso al workspace (rol asignado o super admin).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Parámetros**: `workspace_id` (UUID) en la URL.

**Respuesta exitosa (200)**:
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

**Implementación Frontend**:

1. **Uso**: Página de detalle del workspace, o rellenar formulario de edición.
2. **Seguridad**: Solo mostrar la vista si el workspace está en la lista ya cargada (`GET /api/workspaces`) o si esta petición devuelve 200.
3. **Errores**:
   - `404 Not Found`: Workspace no encontrado o sin acceso → mensaje “Workspace no encontrado” y volver a lista o selector.

---

## PUT `/api/workspaces/{id}` – Actualizar workspace

**Propósito**: Actualizar nombre, descripción o estado activo del workspace.

**Permiso**: Acceso al workspace y permiso `workspaces:write` o `workspaces:admin`, o ser super admin.

**Headers**:
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Body** (todos opcionales):
```json
{
  "name": "Nuevo nombre",
  "description": "Nueva descripción",
  "is_active": true
}
```

**Respuesta exitosa (200)**: Mismo objeto que GET `/api/workspaces/{id}` (workspace actualizado).

**Implementación Frontend**:

1. **Visibilidad**: Mostrar “Editar” solo si el usuario tiene permiso (por ejemplo `workspaces:write` o `workspaces:admin` en ese workspace, o `is_super_admin`). Mientras no exista endpoint de permisos por workspace, puede mostrarse para super admin y para usuarios con rol que se considere editor (ej. `workspace_admin`).
2. **Formulario**: Pre-rellenar con datos de GET `/api/workspaces/{id}` o con el item de la lista. Enviar solo campos modificados si el backend lo acepta (actualmente el backend acepta todos opcionales).
3. **Envío**: `PUT /api/workspaces/{workspace_id}` con body `WorkspaceUpdate`.
4. **Tras éxito**: Actualizar el workspace en el store y en la lista; cerrar modal o volver a detalle.
5. **Errores**:
   - `403 Forbidden`: “Sin permiso para editar este workspace”.
   - `404 Not Found`: “Workspace no encontrado o sin acceso”.

---

## DELETE `/api/workspaces/{id}` – Desactivar workspace

**Propósito**: Desactivar el workspace (soft delete: `is_active = false`). No borra datos.

**Permiso**: Acceso al workspace y permiso `workspaces:delete` o `workspaces:admin`, o ser super admin.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Respuesta exitosa (200)**:
```json
{
  "message": "Workspace desactivado",
  "workspace_id": "uuid-workspace"
}
```

**Implementación Frontend**:

1. **Visibilidad**: Mostrar “Desactivar” (o “Eliminar”) solo si el usuario tiene permiso (p. ej. `workspaces:delete` o `workspaces:admin`, o super admin).
2. **Confirmación**: Siempre pedir confirmación (“¿Desactivar este workspace? No se borrarán los datos.”).
3. **Envío**: `DELETE /api/workspaces/{workspace_id}`.
4. **Tras éxito**: Quitar el workspace de la lista en el store (o marcarlo como `is_active: false` y filtrarlo en la UI). Si el workspace desactivado era el seleccionado, limpiar selección o elegir otro.
5. **Errores**:
   - `403 Forbidden`: “Sin permiso para desactivar este workspace”.
   - `404 Not Found`: “Workspace no encontrado o sin acceso”.

---

## Integración con RBAC y flujo de la app

- **Carga inicial** (ver [GUIA-DESARROLLADOR-FRONTEND.md](../GUIA-DESARROLLADOR-FRONTEND.md), “Al Cargar la Aplicación”):
  1. Tras login, llamar a `GET /api/workspaces` y guardar la lista en el store.
  2. El selector de workspace debe mostrar solo esta lista (ya filtrada por el backend).
  3. Si la lista está vacía, mostrar mensaje tipo “No tienes acceso a ningún workspace. Contacta a un administrador.” y ocultar acciones que requieran workspace.

- **Jerarquía**:
  - Workspace → Proyectos (cuando exista `GET /api/workspaces/{id}/projects`) → Jobs/Reportes.
  - Primero se elige workspace, luego proyecto dentro de ese workspace.

- **Super admin**:
  - Si `is_super_admin === true`: mostrar botón “Crear workspace” y acciones Editar/Desactivar en workspaces (según política de producto).
  - Para el resto, mostrar solo lista y detalle según permisos.

- **Compatibilidad con requisitos**:
  - El frontend ya esperaba `workspace_id`, `name`, `description` en lista; la API además devuelve `id`, `slug`, `is_active`, `role`, `created_at`, `updated_at`. Usar al menos `workspace_id`/`id`, `name`, `description` para mantener compatibilidad.

---

## Checklist de implementación

Usar este checklist para que el agente de UI verifique la implementación:

### Servicio y tipos
- [ ] Definir interfaces `Workspace`, `WorkspaceCreate`, `WorkspaceUpdate`.
- [ ] Crear función `getWorkspaces()` → `GET /api/workspaces`.
- [ ] Crear función `getWorkspace(id)` → `GET /api/workspaces/{id}`.
- [ ] Crear función `createWorkspace(body)` → `POST /api/workspaces`.
- [ ] Crear función `updateWorkspace(id, body)` → `PUT /api/workspaces/{id}`.
- [ ] Crear función `deactivateWorkspace(id)` → `DELETE /api/workspaces/{id}`.
- [ ] Todas las peticiones envían `Authorization: Bearer <token>`.

### Store y estado
- [ ] Guardar lista de workspaces en el store tras login o al cargar app.
- [ ] Actualizar store tras crear/actualizar/desactivar workspace.

### Listado y selección
- [ ] Mostrar lista de workspaces en selector (dropdown o lista).
- [ ] Mostrar solo workspaces devueltos por la API (sin filtrar por cuenta en frontend).
- [ ] Manejar lista vacía con mensaje claro.

### Crear workspace (solo super admin)
- [ ] Mostrar “Crear workspace” solo si `is_super_admin === true`.
- [ ] Formulario con `name` (requerido), `description` y `slug` opcionales.
- [ ] Tras crear, actualizar lista y opcionalmente seleccionar el nuevo workspace.

### Detalle y edición
- [ ] Vista o modal de detalle usando `GET /api/workspaces/{id}`.
- [ ] Botón “Editar” solo si el usuario tiene permiso (p. ej. write/admin o super admin).
- [ ] Formulario de edición con nombre, descripción, is_active; enviar con PUT.

### Desactivar
- [ ] Botón “Desactivar” solo si el usuario tiene permiso.
- [ ] Confirmación antes de llamar a DELETE.
- [ ] Tras éxito, quitar o marcar como inactivo en la lista y actualizar selección.

### Errores y UX
- [ ] Manejar 401 (redirigir al login).
- [ ] Manejar 403 (mensaje de permisos, no ejecutar acción).
- [ ] Manejar 404 (mensaje “No encontrado” y volver).
- [ ] Manejar 500 (mensaje genérico y reintentar).
- [ ] Mostrar estados de carga (loading) en listado y formularios.

---

**Referencias**:
- [GUIA-DESARROLLADOR-FRONTEND.md](../GUIA-DESARROLLADOR-FRONTEND.md) – Autenticación, RBAC y resto de endpoints.
- [API-WORKSPACES.md](../API-WORKSPACES.md) – Especificación técnica de la API de workspaces en el backend.
