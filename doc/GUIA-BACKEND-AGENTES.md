# 🚀 Guía Rápida para Agentes del Backend

> **Punto de entrada principal** para nuevos agentes que trabajarán en el backend de LogsAnomaly.

**Última actualización**: 2026-02-03

---

## 📋 Tabla de Contenidos

1. [Inicio Rápido](#inicio-rápido)
2. [Arquitectura del Backend](#arquitectura-del-backend)
3. [Estructura de Código](#estructura-de-código)
4. [Servicios Principales](#servicios-principales)
5. [Bases de Datos](#bases-de-datos)
6. [Autenticación y Autorización](#autenticación-y-autorización)
7. [Convenciones y Mejores Prácticas](#convenciones-y-mejores-prácticas)
8. [Testing y Debugging](#testing-y-debugging)
9. [Troubleshooting Común](#troubleshooting-común)
10. [Referencias Rápidas](#referencias-rápidas)

---

## 🎯 Inicio Rápido

### 1. Verificar Configuración

```bash
# Verificar variables de entorno críticas
cat .env | grep -E "OLLAMA_API_KEY|POSTGRES_|MONGODB_|REDIS_|JWT_"

# Verificar que el contenedor está corriendo
docker-compose ps
```

### 2. Estructura del Proyecto

```
data/backend-python/
├── main.py                 # Punto de entrada FastAPI
├── config/                 # Configuración (DB, etc.)
├── models/                 # Modelos Pydantic
├── routes/                 # Endpoints API
├── services/               # Lógica de negocio
├── middleware/             # Middleware (auth, etc.)
├── debug/                  # Tests independientes
└── requirements.txt        # Dependencias Python
```

### 3. Comandos Esenciales

```bash
# Iniciar servicios
docker-compose up -d

# Ver logs del backend
docker-compose logs -f anomaly-detector

# Ejecutar tests
cd data/backend-python
python -m debug.run_all_tests

# Acceder al contenedor
docker-compose exec anomaly-detector bash
```

---

## 🏗️ Arquitectura del Backend

### Stack Tecnológico

- **Framework**: FastAPI (Python 3.11)
- **ASGI Server**: Uvicorn
- **Bases de Datos**:
  - **PostgreSQL**: Metadatos, usuarios, RBAC (schemas: `auth`, `processing`)
  - **MongoDB**: Logs crudos, chunks, resultados de anomalías
  - **Redis**: Cache y Pub/Sub para streaming
  - **Qdrant**: Base de datos vectorial (embeddings)
- **LLM**: Ollama Cloud (via `ollama-client-lib`)
- **ML**: Scikit-learn (Isolation Forest)

### Flujo de Procesamiento

```
1. Upload de archivo → chunk_service.py
2. División en chunks → MongoDB
3. Workers procesan chunks → worker_service.py
4. Detección de anomalías → chunk_processor.py
5. Generación de explicaciones → explanation_service.py
6. Almacenamiento de resultados → MongoDB + PostgreSQL
7. Streaming de resultados → stream_manager.py (Redis Pub/Sub)
```

---

## 📁 Estructura de Código

### Modelos ORM (SQLAlchemy)

Los modelos de tablas PostgreSQL están en **`models/db_models.py`**, generados a partir de `db/init.sql`:

- **Schema `processing`**: `ProcessingJob`, `ProcessingStat`, `Configuration`
- **Schema `auth`**: `User`, `UserSession`, `Module`, `Permission`, `Role`, `RolePermission`, `Workspace`, `Project`, `UserWorkspaceRole`, `UserProjectRole`

Uso para migración incremental a ORM: importar `Base` y los modelos desde `models.db_models` (o `models`). Ver regla en `.cursor/rules/backend-orm-migration.mdc`.

### Principios SOLID Aplicados

- ✅ **SRP**: Cada servicio tiene una única responsabilidad
- ✅ **ISP**: Interfaces segregadas (`LLMClientInterface`)
- ✅ **DIP**: Dependencias inyectadas (composición sobre herencia)

### Organización de Servicios

```
services/
├── auth_service.py          # Autenticación JWT, hash de contraseñas
├── user_service.py          # CRUD de usuarios
├── permission_service.py    # Verificación de permisos RBAC
├── workspace_service.py     # CRUD de workspaces
├── project_service.py      # CRUD de proyectos (por workspace)
├── chunk_service.py         # Gestión de chunks de logs
├── chunk_processor.py       # Procesamiento de chunks (ML)
├── worker_service.py        # Workers para procesamiento paralelo
├── explanation_service.py  # Orquestador de explicaciones LLM
├── monitoring_service.py   # Monitoreo y métricas
├── stream_manager.py       # Gestión de streaming SSE
├── embedding_service.py    # Generación de embeddings
├── qdrant_service.py      # Operaciones con Qdrant
│
├── interfaces/             # Interfaces (ISP)
│   └── llm_client_interface.py
│
├── llm/                    # Cliente LLM
│   └── ollama_client_wrapper.py
│
├── log_analysis/           # Análisis de logs
│   └── log_parser.py
│
├── prompts/                # Construcción de prompts
│   └── prompt_builder.py
│
└── explanation/            # Procesamiento de respuestas
    ├── response_parser.py
    └── fallback_explanation.py
```

---

## 🔧 Servicios Principales

### 1. `auth_service.py`

**Responsabilidad**: Autenticación JWT y hash de contraseñas

**Funciones clave**:
- `authenticate_user(username, password)` → Token JWT
- `get_password_hash(password)` → Hash bcrypt (trunca a 72 bytes)
- `verify_password(plain, hashed)` → Verificación de contraseña

**⚠️ Importante**: Bcrypt limita contraseñas a 72 bytes. El código trunca automáticamente.

### 2. `user_service.py`

**Responsabilidad**: CRUD completo de usuarios

**Funciones clave**:
- `create_user(...)` → Crea usuario con hash de contraseña
- `get_user_by_id(user_id)` → Obtiene usuario
- `update_user(user_id, ...)` → Actualiza usuario
- `delete_user(user_id)` → Soft delete
- `list_users(...)` → Lista usuarios con paginación

**Permisos**:
- Registro público: `POST /users` sin token
- Super admin: Acceso completo a todos los endpoints

### 3. `workspace_service.py`

**Responsabilidad**: CRUD de workspaces y listado según permisos del usuario.

**Funciones clave**:
- `create_workspace(name, description, slug, created_by)` → UUID del workspace creado
- `get_workspace_by_id(workspace_id)` → Diccionario con datos del workspace
- `list_workspaces_for_user(user_id)` → Lista de workspaces accesibles (usa `permission_service.get_user_workspaces`)
- `update_workspace(workspace_id, name, description, is_active, slug)` → bool
- `deactivate_workspace(workspace_id)` → Soft delete (is_active = false)

**Slug**: Si no se proporciona, se genera desde el nombre (único en BD). Ver [API-WORKSPACES.md](./API-WORKSPACES.md).

### 4. `project_service.py`

**Responsabilidad**: CRUD de proyectos y listado por workspace según permisos.

**Funciones clave**:
- `list_projects_for_user_in_workspace(user_id, workspace_id)` → Lista de proyectos accesibles en el workspace
- `create_project(workspace_id, name, description, slug, created_by)` → UUID del proyecto creado
- `get_project_by_id(project_id)` → Diccionario con datos del proyecto
- `update_project(project_id, name, description, is_active, slug)` → bool
- `deactivate_project(project_id)` → Soft delete (is_active = false)

**Rutas**: Listado y creación en `routes/workspaces.py` (`GET/POST /workspaces/{id}/projects`); get/update/delete en `routes/projects.py` (`GET/PUT/DELETE /projects/{id}`). Ver [API-PROJECTS.md](./API-PROJECTS.md).

### 5. `explanation_service.py`

**Responsabilidad**: Orquestar generación de explicaciones LLM

**Componentes**:
- `LogParser`: Extrae información de logs
- `PromptBuilder`: Construye prompts para LLM
- `OllamaClientWrapper`: Cliente para Ollama Cloud
- `ResponseParser`: Parsea respuestas del LLM
- `FallbackExplanationGenerator`: Genera explicaciones de respaldo

**Uso**:
```python
from services.explanation_service import explanation_service

explanation = await explanation_service.get_llm_explanation(
    log_entry="...",
    score=0.95
)
```

### 6. `chunk_processor.py`

**Responsabilidad**: Procesar chunks y detectar anomalías

**Flujo**:
1. Recibe chunk de MongoDB
2. Aplica Isolation Forest (ML)
3. Genera explicaciones para anomalías
4. Almacena resultados

### 7. `worker_service.py`

**Responsabilidad**: Gestionar workers paralelos para procesamiento

**Configuración**:
- `max_workers`: Número de workers (actualmente 1)
- Procesa chunks pendientes de PostgreSQL

---

## 🗄️ Bases de Datos

### PostgreSQL (Schemas)

**Schema `auth`**: Autenticación y autorización
- `users`: Usuarios del sistema
- `workspaces`: Espacios de trabajo
- `projects`: Proyectos dentro de workspaces
- `roles`: Roles RBAC
- `permissions`: Permisos (formato: `module:action`)

**Schema `processing`**: Procesamiento de logs
- `processing_jobs`: Jobs de procesamiento
- `chunks`: Chunks pendientes/procesados

**Configuración**:
- `search_path`: `auth,processing,public` (configurado en `database.py`)
- Las queries pueden omitir el schema si está en `search_path`

### MongoDB

**Colecciones principales**:
- `chunks`: Chunks de logs crudos
- `anomaly_results`: Resultados de detección de anomalías

### Redis

**Uso**:
- Cache de resultados
- Pub/Sub para streaming SSE (`/api/results/{job_id}/stream`)

### Qdrant

**Uso**:
- Almacenamiento de embeddings vectoriales
- Búsqueda de similitud semántica

---

## 🔐 Autenticación y Autorización

### JWT Tokens

**Configuración** (`.env`):
```env
JWT_SECRET_KEY=tu_secret_key_aqui
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

**Claims del token**:
- `user_id`: UUID del usuario
- `is_super_admin`: Boolean
- `exp`: Expiración

### Middleware

**`middleware/auth_middleware.py`**:
- `get_current_user`: Requiere token válido
- `get_current_user_optional`: Token opcional (para registro público)
- `require_super_admin`: Requiere super admin

**Uso en rutas**:
```python
from middleware.auth_middleware import get_current_user, CurrentUser

@router.get("/protected")
async def protected_endpoint(
    current_user: CurrentUser = Depends(get_current_user)
):
    return {"user_id": current_user.user_id}
```

### RBAC (Role-Based Access Control)

**Sistema completo**:
- Workspaces → Projects → Roles → Permissions
- Super Admin: Acceso total (bypass de permisos)
- Permisos formato: `module:action` (ej: `logs:read`, `projects:write`)

**Verificación**:
```python
from services.permission_service import check_permission

has_permission = await check_permission(
    user_id=user_id,
    project_id=project_id,
    module="logs",
    action="read"
)
```

---

## 📝 Convenciones y Mejores Prácticas

### 1. Variables de Entorno

**✅ SIEMPRE usar variables de entorno**:
```python
import os

api_key = os.getenv("OLLAMA_API_KEY")
if not api_key:
    raise ValueError("OLLAMA_API_KEY requerida")
```

**❌ NUNCA hardcodear valores**:
```python
# ❌ MAL
api_key = "hardcoded_key"

# ✅ BIEN
api_key = os.getenv("OLLAMA_API_KEY")
```

### 2. Manejo de Errores

**Usar logging apropiado**:
```python
import logging

logger = logging.getLogger(__name__)

try:
    # código
except Exception as e:
    logger.error(f"Error procesando chunk: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### 3. Type Hints

**Siempre usar type hints**:
```python
from typing import Optional, List, Dict
from uuid import UUID

async def get_user(user_id: UUID) -> Optional[Dict]:
    ...
```

### 4. Documentación de Funciones

**Docstrings claros**:
```python
async def create_user(
    email: str,
    username: str,
    password: str
) -> Optional[UUID]:
    """
    Crea un nuevo usuario.
    
    Args:
        email: Email del usuario
        username: Nombre de usuario único
        password: Contraseña en texto plano (se hashea automáticamente)
    
    Returns:
        UUID del usuario creado o None si hay error
    
    Raises:
        ValueError: Si el usuario ya existe
    """
```

### 5. Principio de Responsabilidad Única

**✅ Cada servicio una responsabilidad**:
- `auth_service.py`: Solo autenticación
- `user_service.py`: Solo CRUD de usuarios
- `explanation_service.py`: Solo orquestación de explicaciones

**❌ No mezclar responsabilidades**:
```python
# ❌ MAL: Mezcla parsing + LLM + almacenamiento
class BadService:
    def parse_and_explain_and_save(self):
        ...

# ✅ BIEN: Servicios separados
class LogParser:
    def parse(self): ...

class ExplanationService:
    def __init__(self, parser: LogParser):
        self.parser = parser
```

---

## 🧪 Testing y Debugging

### Tests Independientes (`debug/`)

**Estructura**:
```
debug/
├── test_log_parser.py
├── test_prompt_builder.py
├── test_ollama_client.py
├── test_explanation_service.py
└── run_all_tests.py
```

**Ejecutar tests**:
```bash
cd data/backend-python

# Test individual
python -m debug.test_log_parser

# Todos los tests
python -m debug.run_all_tests
```

### Probar Autenticación JWT

**Login y obtener token**:
```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"ctangarife","password":"1nt3r4ct1v3"}'
```

**Obtener usuario actual**:
```bash
curl -X GET http://localhost/api/auth/me \
  -H "Authorization: Bearer <token>"
```

### Probar Streaming de Ollama

**Requisitos**: `OLLAMA_API_KEY` configurada en `.env`

```bash
cd data/backend-python
python -m debug.test_ollama_client
```

Este test ejecuta:
1. Creación del cliente
2. Verificación de disponibilidad
3. Generación simple
4. Generación en streaming (tiempo real)

### Logs del Backend

```bash
# Ver logs en tiempo real
docker-compose logs -f anomaly-detector

# Ver últimas 100 líneas
docker-compose logs --tail=100 anomaly-detector

# Filtrar por error
docker-compose logs anomaly-detector | grep ERROR
```

### Debugging Interactivo

```bash
# Acceder al contenedor
docker-compose exec anomaly-detector bash

# Python interactivo
python
>>> from config.database import db_manager
>>> await db_manager.connect_all()
```

---

## 🔧 Troubleshooting Común

### Errores de Contraseñas

#### `password cannot be longer than 72 bytes`
**Causa**: Bcrypt limita contraseñas a 72 bytes.  
**Solución**: Ya implementado - el código trunca automáticamente antes de hashear.

#### `password authentication failed for user "anomaly_user"` (PostgreSQL)
**Causa**: Contraseña en PostgreSQL no coincide con `.env`.  
**Solución**:
```bash
# Verificar contraseña en .env
cat .env | grep POSTGRES_PASSWORD

# Cambiar contraseña directamente en PostgreSQL
docker-compose exec postgres psql -U anomaly_user -d logsanomaly
ALTER USER anomaly_user WITH PASSWORD 'contraseña_del_env';
```

### Errores de Bases de Datos

#### `Authentication failed` (MongoDB)
**Causa**: Credenciales incorrectas o volumen no inicializado.  
**Solución**:
```bash
# Verificar que coincidan en .env
MONGO_INITDB_ROOT_PASSWORD=...
MONGODB_URI=mongodb://admin:...@mongodb:27017/...

# Si cambiaron las credenciales, reinicializar volumen
docker-compose down
docker volume rm logsanomaly_mongodb_data
docker-compose up -d mongodb
# Esperar 30-60 segundos, luego:
docker-compose up -d
```

**⚠️ Nota**: Reinicializar MongoDB elimina todos los datos.

### Errores de Dependencias

#### `ModuleNotFoundError: No module named 'ollama-client-lib'`
**Solución**:
```bash
docker-compose exec anomaly-detector pip install -r requirements.txt
docker-compose restart anomaly-detector
```

#### `AttributeError: module 'bcrypt' has no attribute '__about__'`
**Causa**: Versión incompatible de bcrypt.  
**Solución**: Verificar `requirements.txt` tiene `bcrypt==4.0.1`

### Errores de Routing

#### `404 Not Found` en rutas `/api/users`
**Causa**: Nginx no está configurado correctamente.  
**Verificar**:
- `server/nginx/conf.d/default.conf`: `location /api/` debe tener `proxy_pass http://anomaly-detector/`
- Backend corriendo: `docker-compose ps anomaly-detector`

#### `403 Forbidden` al crear usuario
**Causa**: Endpoint requiere super admin o registro público sin token.  
**Solución**: 
- Registro público: `POST /api/users` sin header `Authorization`
- Crear como admin: Incluir token de super admin

### Errores de Streaming

#### Streaming de Ollama no funciona
**Verificar**:
```bash
# API Key configurada
cat .env | grep OLLAMA_API_KEY

# Probar conexión
cd data/backend-python
python -m debug.test_ollama_client
```

#### Modelo no disponible
- Verificar que el modelo existe en Ollama Cloud
- Verificar acceso con la API key
- Probar otro modelo: `OLLAMA_MODEL=phi3:mini`

---

## 📚 Referencias Rápidas

### Documentos Importantes

- **[CONTEXTO-AGENTES-NUEVOS.md](./CONTEXTO-AGENTES-NUEVOS.md)**: Cambios recientes y contexto histórico
- **[API-USUARIOS-CRUD.md](./API-USUARIOS-CRUD.md)**: Documentación completa de API de usuarios
- **[API-WORKSPACES.md](./API-WORKSPACES.md)**: Documentación completa de API de workspaces
- **[API-PROJECTS.md](./API-PROJECTS.md)**: Documentación completa de API de proyectos
- **[CONFIGURACION-MODELOS.md](./CONFIGURACION-MODELOS.md)**: Configuración de modelos LLM
- **[DOCUMENTACION-MAESTRA.md](./DOCUMENTACION-MAESTRA.md)**: Visión general del proyecto

### Endpoints Principales

**Autenticación**:
- `POST /api/auth/login` → Login y obtener token JWT
- `GET /api/auth/me` → Obtener usuario actual

**Usuarios** (ver [API-USUARIOS-CRUD.md](./API-USUARIOS-CRUD.md) para detalles completos):
- `POST /api/users` → Crear usuario (público sin token, o super admin con token)
- `GET /api/users` → Listar usuarios (super admin, con paginación)
- `GET /api/users/count` → Contar usuarios (super admin)
- `GET /api/users/{user_id}` → Obtener usuario (self o super admin)
- `PUT /api/users/{user_id}` → Actualizar usuario (self o super admin)
- `PATCH /api/users/{user_id}/password` → Cambiar contraseña (self o super admin)
- `PATCH /api/users/{user_id}/toggle-active` → Activar/desactivar (super admin)
- `DELETE /api/users/{user_id}` → Eliminar usuario soft delete (super admin)

**Workspaces** (ver [API-WORKSPACES.md](./API-WORKSPACES.md) para detalles completos):
- `GET /api/workspaces` → Listar workspaces accesibles por el usuario
- `POST /api/workspaces` → Crear workspace (super admin)
- `GET /api/workspaces/{workspace_id}` → Obtener workspace (con acceso)
- `PUT /api/workspaces/{workspace_id}` → Actualizar workspace (permiso write/admin)
- `DELETE /api/workspaces/{workspace_id}` → Desactivar workspace (permiso delete/admin)
- `GET /api/workspaces/{workspace_id}/projects` → Listar proyectos del workspace (con acceso)
- `POST /api/workspaces/{workspace_id}/projects` → Crear proyecto en el workspace (permiso projects:write/admin)

**Proyectos** (ver [API-PROJECTS.md](./API-PROJECTS.md) para detalles completos):
- `GET /api/projects/{project_id}` → Obtener proyecto (con acceso)
- `PUT /api/projects/{project_id}` → Actualizar proyecto (permiso write/admin)
- `DELETE /api/projects/{project_id}` → Desactivar proyecto (permiso delete/admin)

### Variables de Entorno Críticas

```env
# Ollama Cloud
OLLAMA_API_KEY=...
OLLAMA_URL=https://ollama.com
OLLAMA_MODEL=qwen2.5:3b

# PostgreSQL
POSTGRES_USER=anomaly_user
POSTGRES_PASSWORD=...
POSTGRES_DB=logsanomaly
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# MongoDB
MONGODB_URI=mongodb://admin:password@mongodb:27017/logsanomaly?authSource=admin

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Comandos Docker Útiles

```bash
# Ver estado de servicios
docker-compose ps

# Reiniciar servicio específico
docker-compose restart anomaly-detector

# Ver logs de un servicio
docker-compose logs -f anomaly-detector

# Ejecutar comando en contenedor
docker-compose exec anomaly-detector python -m debug.test_log_parser

# Reconstruir imagen
docker-compose build anomaly-detector
```

---

## ✅ Checklist para Nuevos Agentes

Antes de empezar a trabajar:

- [ ] Leer esta guía completa
- [ ] Verificar que `.env` tiene todas las variables necesarias
- [ ] Ejecutar `docker-compose up -d` y verificar que todos los servicios están corriendo
- [ ] Ejecutar tests: `python -m debug.run_all_tests`
- [ ] Probar login: `curl -X POST http://localhost/api/auth/login ...`
- [ ] Revisar estructura de código en `services/`
- [ ] Entender el flujo de procesamiento de logs

---

## 📚 Documentación Adicional

- **[API-USUARIOS-CRUD.md](./API-USUARIOS-CRUD.md)**: Documentación completa de endpoints de usuarios con ejemplos
- **[API-WORKSPACES.md](./API-WORKSPACES.md)**: Documentación completa de endpoints de workspaces
- **[API-PROJECTS.md](./API-PROJECTS.md)**: Documentación completa de endpoints de proyectos
- **[CONFIGURACION-MODELOS.md](./CONFIGURACION-MODELOS.md)**: Configuración detallada de modelos LLM
- **[DOCUMENTACION-MAESTRA.md](./DOCUMENTACION-MAESTRA.md)**: Visión general completa del proyecto
- **[ARQUITECTURA-RABBITMQ.md](./ARQUITECTURA-RABBITMQ.md)**: Arquitectura de mensajería asíncrona

---

**¿Necesitas ayuda?** Revisa los documentos en `doc/` o consulta el código fuente con comentarios detallados.

**Última actualización**: 2026-02-03
**Mantener actualizado**: Agregar cambios importantes aquí para futuros agentes
