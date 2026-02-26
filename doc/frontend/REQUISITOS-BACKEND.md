# Requisitos Backend - Frontend

Este documento especifica los requisitos que el backend debe cumplir para que el frontend funcione correctamente.

## Endpoints Requeridos

### Autenticación

#### POST `/api/auth/login`

**Descripción**: Endpoint para autenticación de usuarios.

**Request**:
```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

**Response Exitosa (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "usuario",
    "is_super_admin": false
  }
}
```

**Response Error (401)**:
```json
{
  "detail": "Credenciales inválidas"
}
```

**Requisitos**:
- El token JWT debe incluir `user_id` y `is_super_admin` en los claims
- El token debe tener una expiración razonable (ej: 24 horas)
- El formato del token debe ser decodificable en el frontend

---

#### GET `/api/auth/me`

**Descripción**: Obtener información del usuario actual desde el token.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Response Exitosa (200)**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "usuario",
  "is_super_admin": false
}
```

**Requisitos**:
- Debe extraer información del token JWT
- Debe retornar 401 si el token es inválido o expirado

---

### Workspaces y Proyectos

#### GET `/api/workspaces`

**Descripción**: Obtener todos los workspaces accesibles por el usuario.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Response Exitosa (200)**:
```json
[
  {
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Departamento de IT",
    "description": "Workspace principal"
  }
]
```

**Requisitos**:
- Debe filtrar workspaces según permisos del usuario
- Super admin debe ver todos los workspaces
- Debe retornar array vacío si no hay workspaces accesibles

---

#### GET `/api/workspaces/{workspace_id}/projects`

**Descripción**: Obtener todos los proyectos accesibles en un workspace.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Response Exitosa (200)**:
```json
[
  {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Análisis de logs de producción",
    "description": "Proyecto principal",
    "workspace_id": "550e8400-e29b-41d4-a716-446655440000"
  }
]
```

**Requisitos**:
- Debe verificar que el usuario tiene acceso al workspace
- Debe filtrar proyectos según permisos del usuario
- Super admin debe ver todos los proyectos
- Debe retornar 403 si no tiene acceso al workspace

---

#### GET `/api/projects/{project_id}/permissions`

**Descripción**: Obtener permisos del usuario en un proyecto específico.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Response Exitosa (200)**:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "permissions": [
    "logs:read",
    "logs:write",
    "anomalies:read"
  ],
  "roles": [
    {
      "role_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Analista",
      "permissions": ["logs:read", "logs:write", "anomalies:read"]
    }
  ]
}
```

**Requisitos**:
- Debe verificar que el usuario tiene acceso al proyecto
- Debe retornar todos los permisos efectivos (incluyendo herencia de workspace)
- Super admin debe retornar todos los permisos disponibles
- Debe retornar 403 si no tiene acceso al proyecto

---

### Procesamiento (Ya Implementados)

Los siguientes endpoints ya están implementados según `GUIA-DESARROLLADOR-FRONTEND.md`:

- ✅ POST `/api/process`
- ✅ GET `/api/status/{job_id}`
- ✅ GET `/api/results/{job_id}/stream` (ver detalles de arquitectura RabbitMQ abajo)
- ✅ POST `/api/cancel/{job_id}`
- ✅ GET `/api/reports`
- ✅ GET `/api/monitoring/dashboard`

**Nota**: Estos endpoints deben incluir verificación de permisos según se especifica en la guía.

---

## Arquitectura de Streaming SSE con RabbitMQ

### GET `/api/results/{job_id}/stream`

**Arquitectura Detallada**:

El sistema usa **RabbitMQ** para el streaming SSE (no Redis Pub/Sub) porque ofrece:
- **Persistencia**: Si el cliente se desconecta, puede reconectarse y recibir mensajes perdidos
- **Garantías de entrega**: Los mensajes se entregan de forma confiable
- **Escalabilidad**: Múltiples clientes pueden escuchar el mismo job eficientemente

**Cómo Funciona**:

1. **Creación de Cola**: Cuando se inicia un job, el backend debe crear una cola RabbitMQ dedicada:
   - Nombre de cola: `job.{job_id}.stream`
   - Tipo: Cola durable (sobrevive reinicios)
   - Binding: Conectada al Exchange `anomaly_detection` con routing key `job.{job_id}.stream`

2. **Publicación de Mensajes**: Los workers publican actualizaciones al Exchange RabbitMQ:
   - Exchange: `anomaly_detection` (Topic Exchange)
   - Routing Key: `job.{job_id}.stream`
   - Formato del mensaje: JSON con estructura SSE

3. **Consumo SSE**: El endpoint `/api/results/{job_id}/stream`:
   - Consume mensajes de la cola `job.{job_id}.stream`
   - Formatea cada mensaje como evento SSE estándar
   - Envía al cliente con `Content-Type: text/event-stream`
   - Mantiene la conexión abierta hasta que el job completa

4. **Reconexión**: Si el cliente se desconecta:
   - Los mensajes quedan en la cola RabbitMQ
   - Al reconectar, el backend entrega los mensajes pendientes
   - No se pierden mensajes durante la desconexión

**Estructura de Mensajes RabbitMQ**:

Los mensajes publicados al Exchange deben tener este formato JSON:

```json
{
  "type": "batch_progress",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_number": 5,
  "chunk_id": "chunk-uuid",
  "progress": 0.33,
  "anomalies": [
    {
      "log_entry": "ERROR: Connection timeout",
      "score": -0.15,
      "is_anomaly": true,
      "explanation": "El servidor está experimentando timeouts...",
      "chunk_id": "chunk-uuid"
    }
  ],
  "timestamp": "2024-01-15T10:30:45Z"
}
```

**Formato SSE de Salida**:

El endpoint debe convertir cada mensaje RabbitMQ a formato SSE:

```
data: {"type": "stream_started", "job_id": "550e8400-e29b-41d4-a716-446655440000"}

data: {"type": "batch_progress", "chunk_number": 1, "anomalies": [...], "progress": 0.1}

data: {"type": "job_completed", "job_id": "550e8400-e29b-41d4-a716-446655440000"}
```

**Tipos de Eventos Requeridos**:

- `stream_started`: Enviado cuando el stream se inicia (primer mensaje)
- `batch_progress`: Nuevo batch de anomalías procesado
- `chunk_progress`: Progreso de procesamiento de chunks (opcional, para updates más frecuentes)
- `job_completed`: Job completado exitosamente
- `error`: Error en el stream o procesamiento

**Limpieza de Recursos**:

- Cuando el job completa o se cancela, el backend debe:
  - Cerrar la conexión SSE
  - Opcionalmente eliminar la cola `job.{job_id}.stream` después de un TTL (ej: 1 hora)
  - O mantener la cola para reconexiones tardías y eliminarla después de un período de inactividad

**Requisitos Técnicos**:

- El endpoint debe mantener la conexión HTTP abierta mientras haya mensajes en la cola
- Debe manejar múltiples clientes conectados al mismo job simultáneamente
- Cada cliente debe recibir todos los mensajes desde el inicio del stream (o desde su conexión)
- Debe manejar desconexiones gracefully sin afectar otros clientes
- Debe incluir headers SSE estándar:
  ```
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive
  ```

**Referencia**: Ver `doc/ARQUITECTURA-RABBITMQ.md` para detalles completos de la arquitectura RabbitMQ.

---

## Comportamiento Esperado de Permisos

### Verificación de Permisos

El backend debe verificar permisos en cada endpoint:

1. **Extraer `user_id` del token JWT**
2. **Verificar si `is_super_admin === true`**:
   - Si es super admin, permitir acceso completo
3. **Si no es super admin**:
   - Verificar permisos específicos según el módulo/acción requerido
   - Verificar acceso al workspace/proyecto según jerarquía RBAC
4. **Retornar 403 Forbidden** si no tiene permisos

### Jerarquía de Permisos

El sistema debe respetar la jerarquía:
- Workspace → Project → Job
- Un usuario debe tener acceso al workspace Y al project para procesar logs

### Filtrado Automático

Los endpoints que retornan listas deben filtrar automáticamente:
- `/api/reports` → Solo reportes de proyectos accesibles
- `/api/workspaces` → Solo workspaces accesibles
- `/api/workspaces/{id}/projects` → Solo proyectos accesibles

---

## Manejo de Errores

### Códigos de Estado HTTP

- `200 OK`: Petición exitosa
- `400 Bad Request`: Datos inválidos
- `401 Unauthorized`: Token faltante, inválido o expirado
- `403 Forbidden`: Usuario no tiene permisos necesarios
- `404 Not Found`: Recurso no encontrado
- `409 Conflict`: Conflicto (ej: ya hay un archivo procesándose)
- `500 Internal Server Error`: Error del servidor

### Formato de Errores

Todas las respuestas de error deben seguir este formato:

```json
{
  "detail": "Mensaje de error descriptivo"
}
```

---

## Notas Importantes

1. **JWT Claims**: El token debe incluir `user_id` y `is_super_admin` para que el frontend pueda funcionar correctamente.

2. **CORS**: El backend debe permitir peticiones desde el frontend (configurar CORS apropiadamente).

3. **Base URL**: Todas las peticiones van a `/api/*` desde el frontend. Nginx hace el rewrite al backend interno.

4. **Streaming SSE con RabbitMQ**: El endpoint `/api/results/{job_id}/stream` debe retornar `text/event-stream` con formato SSE estándar. Ver sección "Arquitectura de Streaming SSE con RabbitMQ" más abajo para detalles completos.

5. **Paginación**: Los endpoints de listas deben soportar `limit` y `offset` para paginación futura.

---

## Prioridad de Implementación

### Alta Prioridad (Crítico para funcionamiento básico)
1. POST `/api/auth/login`
2. GET `/api/auth/me`
3. GET `/api/workspaces`
4. GET `/api/workspaces/{workspace_id}/projects`
5. GET `/api/projects/{project_id}/permissions`

### Media Prioridad (Mejora UX)
- Mejoras en manejo de errores
- Optimizaciones de rendimiento

### Baja Prioridad (Futuro)
- Paginación avanzada
- Filtros adicionales
- Búsqueda en listas

---

**Última actualización**: 2026-02-01
**Versión**: 1.0.0
