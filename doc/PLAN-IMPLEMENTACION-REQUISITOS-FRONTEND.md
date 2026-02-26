# Plan de Implementación - Requisitos Frontend

**Fecha**: 2026-02-01  
**Estado**: Plan de Acción  
**Prioridad**: Alta

---

## 📋 Resumen Ejecutivo

El frontend requiere **5 endpoints nuevos** de autenticación y RBAC que actualmente **NO están implementados** en el backend. Además, se necesita migrar el streaming SSE de Redis Pub/Sub a RabbitMQ y agregar verificación de permisos en todos los endpoints existentes.

---

## ✅ Estado Actual del Backend

### Endpoints Ya Implementados ✅

1. ✅ `POST /api/process` - Procesar archivo
2. ✅ `GET /api/status/{job_id}` - Estado de procesamiento
3. ✅ `GET /api/results/{job_id}/stream` - Streaming SSE (usa Redis Pub/Sub, necesita migrar a RabbitMQ)
4. ✅ `POST /api/cancel/{job_id}` - Cancelar job
5. ✅ `GET /api/reports` - Obtener reportes
6. ✅ `GET /api/monitoring/dashboard` - Dashboard de monitoreo

### Servicios Existentes ✅

- ✅ `permission_service.py` - Servicios de verificación de permisos RBAC
- ✅ `rbac_models.py` - Modelos Pydantic para RBAC
- ✅ Base de datos PostgreSQL con esquema RBAC (`init_rbac.sql`)

### Lo Que FALTA ❌

1. ❌ **Sistema de Autenticación JWT** completo
2. ❌ **Endpoints de autenticación** (`/api/auth/login`, `/api/auth/me`)
3. ❌ **Endpoints de workspaces y proyectos** (`/api/workspaces`, `/api/workspaces/{id}/projects`, `/api/projects/{id}/permissions`)
4. ❌ **Middleware de autenticación** para proteger endpoints
5. ❌ **Verificación de permisos** en endpoints existentes
6. ❌ **Migración de streaming SSE** de Redis a RabbitMQ

---

## 🎯 Requisitos del Frontend

### 1. Autenticación (ALTA PRIORIDAD)

#### POST `/api/auth/login`
- **Estado**: ❌ NO IMPLEMENTADO
- **Requisitos**:
  - Validar credenciales (username/password)
  - Generar JWT con claims: `user_id`, `is_super_admin`
  - Token con expiración (24 horas)
  - Retornar token + información del usuario

#### GET `/api/auth/me`
- **Estado**: ❌ NO IMPLEMENTADO
- **Requisitos**:
  - Extraer `user_id` del token JWT
  - Validar token (no expirado, válido)
  - Retornar información del usuario
  - Retornar 401 si token inválido

### 2. Workspaces y Proyectos (ALTA PRIORIDAD)

#### GET `/api/workspaces`
- **Estado**: ❌ NO IMPLEMENTADO
- **Requisitos**:
  - Filtrar workspaces según permisos del usuario
  - Super admin ve todos los workspaces
  - Retornar array vacío si no hay acceso

#### GET `/api/workspaces/{workspace_id}/projects`
- **Estado**: ❌ NO IMPLEMENTADO
- **Requisitos**:
  - Verificar acceso al workspace
  - Filtrar proyectos según permisos
  - Super admin ve todos los proyectos
  - Retornar 403 si no tiene acceso

#### GET `/api/projects/{project_id}/permissions`
- **Estado**: ❌ NO IMPLEMENTADO
- **Requisitos**:
  - Verificar acceso al proyecto
  - Retornar permisos efectivos del usuario
  - Incluir roles asignados
  - Super admin retorna todos los permisos
  - Retornar 403 si no tiene acceso

### 3. Streaming SSE con RabbitMQ (MEDIA PRIORIDAD)

#### GET `/api/results/{job_id}/stream`
- **Estado**: ⚠️ IMPLEMENTADO PERO USA REDIS (necesita migrar a RabbitMQ)
- **Requisitos**:
  - Migrar de Redis Pub/Sub a RabbitMQ
  - Crear cola `job.{job_id}.stream` cuando se inicia job
  - Consumir mensajes de RabbitMQ y formatear como SSE
  - Manejar reconexión (mensajes no se pierden)
  - Limpiar cola cuando job completa

### 4. Verificación de Permisos en Endpoints Existentes (ALTA PRIORIDAD)

Todos los endpoints existentes deben:
- ✅ Extraer `user_id` del token JWT
- ✅ Verificar permisos según el recurso (proyecto/workspace)
- ✅ Retornar 403 si no tiene permisos
- ✅ Super admin tiene acceso completo

**Endpoints a proteger**:
- `POST /api/process` → Requiere `logs:write` en proyecto
- `GET /api/status/{job_id}` → Requiere `logs:read` en proyecto del job
- `GET /api/results/{job_id}/stream` → Requiere `logs:read` en proyecto del job
- `POST /api/cancel/{job_id}` → Requiere `logs:write` en proyecto del job
- `GET /api/reports` → Requiere `logs:read` (filtrar por proyectos accesibles)
- `GET /api/monitoring/dashboard` → Requiere `monitoring:read`

---

## 📝 Plan de Implementación

### Fase 1: Sistema de Autenticación JWT (Semana 1)

#### Tarea 1.1: Crear servicio de autenticación
- [ ] Crear `services/auth_service.py`
- [ ] Implementar función `authenticate_user(username, password)`
- [ ] Implementar función `create_access_token(user_id, is_super_admin)`
- [ ] Implementar función `verify_token(token)`
- [ ] Usar biblioteca `python-jose[cryptography]` para JWT

#### Tarea 1.2: Crear middleware de autenticación
- [ ] Crear `middleware/auth_middleware.py`
- [ ] Implementar `get_current_user()` dependency de FastAPI
- [ ] Extraer token del header `Authorization: Bearer <token>`
- [ ] Validar token y retornar `user_id` e `is_super_admin`
- [ ] Retornar 401 si token inválido

#### Tarea 1.3: Implementar endpoints de autenticación
- [ ] Crear `routes/auth.py`
- [ ] Implementar `POST /api/auth/login`
- [ ] Implementar `GET /api/auth/me`
- [ ] Registrar rutas en `main.py`

#### Tarea 1.4: Actualizar `requirements.txt`
- [ ] Agregar `python-jose[cryptography]` (ya está comentado)
- [ ] Agregar `passlib[bcrypt]` para hash de contraseñas
- [ ] Verificar que `python-multipart` esté para FormData

### Fase 2: Endpoints de Workspaces y Proyectos (Semana 1)

#### Tarea 2.1: Crear rutas de workspaces
- [ ] Crear `routes/workspaces.py`
- [ ] Implementar `GET /api/workspaces`
- [ ] Usar `permission_service.get_user_workspaces()`
- [ ] Filtrar según permisos (super admin ve todos)

#### Tarea 2.2: Crear rutas de proyectos
- [ ] Crear `routes/projects.py`
- [ ] Implementar `GET /api/workspaces/{workspace_id}/projects`
- [ ] Implementar `GET /api/projects/{project_id}/permissions`
- [ ] Usar servicios de `permission_service.py`
- [ ] Verificar acceso antes de retornar datos

#### Tarea 2.3: Crear modelos de respuesta
- [ ] Actualizar `models/rbac_models.py` con modelos de respuesta
- [ ] `WorkspaceResponse`, `ProjectResponse`, `PermissionsResponse`
- [ ] Incluir información de roles y permisos

### Fase 3: Proteger Endpoints Existentes (Semana 2)

#### Tarea 3.1: Crear dependency de permisos
- [ ] Crear `dependencies/permissions.py`
- [ ] Implementar `require_permission(module, action)`
- [ ] Implementar `get_project_from_job(job_id)`
- [ ] Verificar permisos usando `permission_service`

#### Tarea 3.2: Actualizar endpoints existentes
- [ ] `POST /api/process` → Agregar parámetro `project_id` en request
- [ ] `GET /api/status/{job_id}` → Obtener proyecto del job y verificar `logs:read`
- [ ] `GET /api/results/{job_id}/stream` → Verificar `logs:read`
- [ ] `POST /api/cancel/{job_id}` → Verificar `logs:write`
- [ ] `GET /api/reports` → Filtrar por proyectos accesibles
- [ ] `GET /api/monitoring/dashboard` → Verificar `monitoring:read`

#### Tarea 3.3: Actualizar modelos de request
- [ ] `ProcessRequest` debe incluir `project_id`
- [ ] Actualizar `v2_models.py` con nuevos campos

### Fase 4: Migración Streaming SSE a RabbitMQ (Semana 2-3)

#### Tarea 4.1: Configurar RabbitMQ
- [ ] Agregar RabbitMQ a `docker-compose.yml`
- [ ] Crear servicio de conexión RabbitMQ
- [ ] Configurar Exchange `anomaly_detection` (Topic)
- [ ] Configurar variables de entorno

#### Tarea 4.2: Crear servicio de mensajería RabbitMQ
- [ ] Crear `services/rabbitmq_service.py`
- [ ] Implementar publicación de mensajes
- [ ] Implementar creación de colas dinámicas `job.{job_id}.stream`
- [ ] Implementar consumo de mensajes

#### Tarea 4.3: Migrar endpoint SSE
- [ ] Actualizar `GET /api/results/{job_id}/stream`
- [ ] Cambiar de Redis Pub/Sub a RabbitMQ
- [ ] Crear cola cuando se inicia job
- [ ] Consumir mensajes y formatear como SSE
- [ ] Limpiar cola cuando job completa

#### Tarea 4.4: Actualizar workers
- [ ] Actualizar `worker_service.py` para publicar a RabbitMQ
- [ ] Cambiar `_publish_batch_progress()` para usar RabbitMQ
- [ ] Cambiar `_publish_chunk_progress()` para usar RabbitMQ
- [ ] Cambiar `_publish_job_completed()` para usar RabbitMQ

### Fase 5: Testing y Documentación (Semana 3)

#### Tarea 5.1: Tests de autenticación
- [ ] Test de login exitoso
- [ ] Test de login con credenciales inválidas
- [ ] Test de token expirado
- [ ] Test de token inválido

#### Tarea 5.2: Tests de permisos
- [ ] Test de acceso con permisos válidos
- [ ] Test de acceso sin permisos (403)
- [ ] Test de super admin (acceso completo)
- [ ] Test de filtrado de recursos

#### Tarea 5.3: Tests de streaming RabbitMQ
- [ ] Test de creación de cola
- [ ] Test de publicación de mensajes
- [ ] Test de consumo SSE
- [ ] Test de reconexión

#### Tarea 5.4: Actualizar documentación
- [ ] Actualizar `GUIA-DESARROLLADOR-FRONTEND.md`
- [ ] Documentar nuevos endpoints
- [ ] Documentar sistema de autenticación
- [ ] Crear guía de migración RabbitMQ

---

## 🔧 Detalles Técnicos

### Estructura de Archivos a Crear

```
data/backend-python/
├── services/
│   ├── auth_service.py          # NUEVO: Autenticación JWT
│   └── rabbitmq_service.py      # NUEVO: Servicio RabbitMQ
├── middleware/
│   └── auth_middleware.py        # NUEVO: Middleware de autenticación
├── dependencies/
│   └── permissions.py            # NUEVO: Dependencies de permisos
├── routes/
│   ├── auth.py                   # NUEVO: Rutas de autenticación
│   ├── workspaces.py             # NUEVO: Rutas de workspaces
│   └── projects.py               # NUEVO: Rutas de proyectos
└── models/
    └── rbac_models.py            # ACTUALIZAR: Agregar modelos de respuesta
```

### Dependencias a Agregar

```txt
python-jose[cryptography]>=3.3.0  # JWT
passlib[bcrypt]>=1.7.4            # Hash de contraseñas
aio-pika>=9.0.0                    # Cliente RabbitMQ async
```

### Variables de Entorno a Agregar

```bash
# JWT
JWT_SECRET_KEY=<secret_key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_EXCHANGE=anomaly_detection
```

---

## ⚠️ Consideraciones Importantes

### 1. Compatibilidad con Frontend

- El frontend **YA ESTÁ IMPLEMENTADO** y espera estos endpoints
- Los endpoints deben coincidir **EXACTAMENTE** con los especificados en `REQUISITOS-BACKEND.md`
- Los formatos de respuesta deben ser idénticos

### 2. Base de Datos

- El esquema RBAC ya existe en PostgreSQL (`init_rbac.sql`)
- Verificar que las funciones SQL (`user_has_project_permission`, etc.) existan
- Asegurar que hay datos de prueba (usuarios, workspaces, proyectos)

### 3. Seguridad

- **NUNCA** exponer contraseñas en logs
- Usar hash bcrypt para contraseñas
- Validar y sanitizar todos los inputs
- Implementar rate limiting en `/api/auth/login`

### 4. Migración Gradual

- Implementar autenticación primero (Fase 1)
- Luego proteger endpoints existentes (Fase 3)
- Finalmente migrar streaming (Fase 4)
- Mantener Redis como fallback temporal

---

## 📊 Priorización

### Crítico (Bloquea Frontend)
1. ✅ **Fase 1**: Sistema de autenticación JWT
2. ✅ **Fase 2**: Endpoints de workspaces/proyectos
3. ✅ **Fase 3**: Proteger endpoints existentes

### Importante (Mejora UX)
4. ⚠️ **Fase 4**: Migración streaming a RabbitMQ

### Opcional (Futuro)
5. 📝 **Fase 5**: Testing y documentación

---

## 🚀 Siguiente Paso Inmediato

**Comenzar con Fase 1, Tarea 1.1**: Crear `services/auth_service.py` con funciones básicas de autenticación.

---

**Última actualización**: 2026-02-01  
**Versión**: 1.0.0
