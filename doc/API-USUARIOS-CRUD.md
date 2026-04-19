# API CRUD de Usuarios

**Endpoint base**: `/api/users`

## Autenticación

Todos los endpoints requieren autenticación JWT mediante el header:
```
Authorization: Bearer <token>
```

## Endpoints

### 1. Crear Usuario

**POST** `/api/users`

**Permisos**: Solo super administradores

**Request Body**:
```json
{
  "email": "usuario@example.com",
  "username": "usuario123",
  "password": "contraseña123",
  "full_name": "Nombre Completo"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid-del-usuario",
  "email": "usuario@example.com",
  "username": "usuario123",
  "full_name": "Nombre Completo",
  "is_active": true,
  "is_super_admin": false,
  "last_login": null,
  "created_at": "2026-02-01T12:00:00Z",
  "updated_at": "2026-02-01T12:00:00Z"
}
```

**Errores**:
- `409 Conflict`: El usuario o email ya existe
- `403 Forbidden`: No tienes permisos de super administrador
- `400 Bad Request`: Datos inválidos (contraseña muy corta, email inválido, etc.)

---

### 2. Listar Usuarios

**GET** `/api/users`

**Permisos**: Solo super administradores

**Query Parameters**:
- `skip` (int, default: 0): Número de registros a saltar
- `limit` (int, default: 100, max: 1000): Número máximo de registros
- `is_active` (bool, optional): Filtrar por estado activo/inactivo
- `search` (string, optional): Buscar por username o email

**Ejemplo**:
```
GET /api/users?skip=0&limit=50&is_active=true&search=admin
```

**Response** (200 OK):
```json
[
  {
    "id": "uuid-1",
    "email": "usuario1@example.com",
    "username": "usuario1",
    "full_name": "Usuario Uno",
    "is_active": true,
    "is_super_admin": false,
    "last_login": "2026-02-01T10:00:00Z",
    "created_at": "2026-01-01T12:00:00Z",
    "updated_at": "2026-02-01T12:00:00Z"
  },
  {
    "id": "uuid-2",
    "email": "usuario2@example.com",
    "username": "usuario2",
    "full_name": "Usuario Dos",
    "is_active": true,
    "is_super_admin": true,
    "last_login": null,
    "created_at": "2026-01-15T12:00:00Z",
    "updated_at": "2026-01-15T12:00:00Z"
  }
]
```

---

### 3. Contar Usuarios

**GET** `/api/users/count`

**Permisos**: Solo super administradores

**Query Parameters**:
- `is_active` (bool, optional): Filtrar por estado activo/inactivo

**Response** (200 OK):
```json
{
  "total": 42
}
```

---

### 4. Obtener Usuario por ID

**GET** `/api/users/{user_id}`

**Permisos**: 
- El mismo usuario puede ver su propio perfil
- Super administradores pueden ver cualquier usuario

**Response** (200 OK):
```json
{
  "id": "uuid-del-usuario",
  "email": "usuario@example.com",
  "username": "usuario123",
  "full_name": "Nombre Completo",
  "is_active": true,
  "is_super_admin": false,
  "last_login": "2026-02-01T10:00:00Z",
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-02-01T12:00:00Z"
}
```

**Errores**:
- `404 Not Found`: Usuario no encontrado
- `403 Forbidden`: No tienes permisos para ver este usuario

---

### 5. Actualizar Usuario

**PUT** `/api/users/{user_id}`

**Permisos**: 
- El mismo usuario puede actualizar su propia información básica
- Super administradores pueden actualizar cualquier usuario

**Request Body** (todos los campos son opcionales):
```json
{
  "email": "nuevo@example.com",
  "username": "nuevo_usuario",
  "full_name": "Nuevo Nombre",
  "is_active": true
}
```

**Notas**:
- Los usuarios normales NO pueden cambiar `is_active`
- Solo super administradores pueden cambiar `is_active`
- `is_super_admin` NO se puede cambiar mediante este endpoint (usar endpoint específico si es necesario)

**Response** (200 OK):
```json
{
  "id": "uuid-del-usuario",
  "email": "nuevo@example.com",
  "username": "nuevo_usuario",
  "full_name": "Nuevo Nombre",
  "is_active": true,
  "is_super_admin": false,
  "last_login": "2026-02-01T10:00:00Z",
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-02-01T13:00:00Z"
}
```

**Errores**:
- `404 Not Found`: Usuario no encontrado
- `403 Forbidden`: No tienes permisos para actualizar este usuario
- `409 Conflict`: El username o email ya está en uso

---

### 6. Cambiar Contraseña

**PATCH** `/api/users/{user_id}/password`

**Permisos**: 
- El mismo usuario puede cambiar su propia contraseña
- Super administradores pueden cambiar cualquier contraseña

**Request Body**:
```json
{
  "new_password": "nueva_contraseña_segura"
}
```

**Response** (200 OK):
```json
{
  "message": "Contraseña actualizada exitosamente"
}
```

**Errores**:
- `400 Bad Request`: La contraseña debe tener al menos 8 caracteres
- `404 Not Found`: Usuario no encontrado
- `403 Forbidden`: No tienes permisos para cambiar esta contraseña

---

### 7. Activar/Desactivar Usuario

**PATCH** `/api/users/{user_id}/toggle-active`

**Permisos**: Solo super administradores

**Response** (200 OK):
```json
{
  "id": "uuid-del-usuario",
  "email": "usuario@example.com",
  "username": "usuario123",
  "full_name": "Nombre Completo",
  "is_active": false,
  "is_super_admin": false,
  "last_login": "2026-02-01T10:00:00Z",
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-02-01T13:00:00Z"
}
```

**Notas**:
- No puedes desactivar tu propia cuenta
- Este endpoint hace un "toggle" del estado actual

**Errores**:
- `404 Not Found`: Usuario no encontrado
- `403 Forbidden`: No tienes permisos de super administrador
- `400 Bad Request`: No puedes desactivar tu propia cuenta

---

### 8. Eliminar Usuario

**DELETE** `/api/users/{user_id}`

**Permisos**: Solo super administradores

**Response** (204 No Content)

**Notas**:
- Es un "soft delete": marca el usuario como inactivo (`is_active = false`)
- No puedes eliminar tu propia cuenta
- El usuario sigue existiendo en la base de datos pero no puede iniciar sesión

**Errores**:
- `404 Not Found`: Usuario no encontrado
- `403 Forbidden`: No tienes permisos de super administrador
- `400 Bad Request`: No puedes eliminar tu propia cuenta

---

## Ejemplos de Uso

### Crear un usuario (Super Admin)

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@example.com",
    "username": "nuevo_usuario",
    "password": "contraseña123",
    "full_name": "Usuario Nuevo"
  }'
```

### Listar usuarios activos

```bash
curl -X GET "http://localhost:8000/api/users?is_active=true&limit=50" \
  -H "Authorization: Bearer <token>"
```

### Actualizar mi propio perfil

```bash
curl -X PUT http://localhost:8000/api/users/{mi_user_id} \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Mi Nuevo Nombre"
  }'
```

### Cambiar mi contraseña

```bash
curl -X PATCH http://localhost:8000/api/users/{mi_user_id}/password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "nueva_contraseña_segura"
  }'
```

---

**Última actualización**: 2026-02-01
