# 📚 Documentación Maestra - LogsAnomaly

**Última actualización:** 18 de diciembre de 2025  
**Versión:** 2.0.0  
**Estado:** Documentación consolidada para agentes desarrolladores

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Contexto del Proyecto](#contexto-del-proyecto)
3. [Arquitectura Actual](#arquitectura-actual)
4. [Arquitectura Propuesta: Backends Separados](#arquitectura-propuesta-backends-separados)
5. [Sistema RBAC](#sistema-rbac)
6. [Enfoque Educativo](#enfoque-educativo)
7. [Implementaciones Técnicas](#implementaciones-técnicas)
8. [Stack Tecnológico](#stack-tecnológico)
9. [Estructura del Proyecto](#estructura-del-proyecto)
10. [Tareas y Roadmap](#tareas-y-roadmap)
11. [Referencias Técnicas](#referencias-técnicas)

---

## 🎯 Resumen Ejecutivo

**LogsAnomaly** es un sistema de detección de anomalías en logs que combina Machine Learning (Isolation Forest) con IA local (Ollama) para identificar y explicar comportamientos sospechosos en logs.

### Filosofía del Sistema

**"No competir con herramientas de detección avanzadas, sino ayudar a analistas a entender mejor lo que encuentran"**

- **Enfoque:** Educativo y contextual, no solo detección técnica
- **Objetivo:** Ayudar a analistas junior/intermedios a comprender, priorizar y actuar sobre anomalías
- **Diferencia:** Contexto educativo, comparaciones, visualizaciones y guías accionables

### Características Principales

- ✅ Procesamiento de archivos grandes (hasta 2GB)
- ✅ Detección de anomalías con Isolation Forest
- ✅ Explicaciones en lenguaje natural con LLM local
- ✅ Arquitectura multi-DB (MongoDB, PostgreSQL, Redis, Qdrant)
- ✅ Sistema RBAC con workspaces y proyectos
- ✅ Enfoque educativo con contexto y comparaciones
- ✅ Búsqueda de similitud con embeddings vectoriales

---

## 📖 Contexto del Proyecto

### Descripción General

LogsAnomaly procesa archivos de logs de gran tamaño, detecta patrones anómalos usando algoritmos de machine learning, y proporciona explicaciones educativas en lenguaje natural sobre las anomalías detectadas.

### Capacidades Actuales

- **Tamaño de archivos:** Hasta 2GB
- **Procesamiento:** Chunks de 1MB, 4-8 workers paralelos
- **Bases de datos:** MongoDB (logs), PostgreSQL (metadatos), Redis (cache), Qdrant (vectores)
- **IA:** Ollama con modelos configurables (por defecto: qwen2.5:3b)
- **Frontend:** Vue 3 + TypeScript + PrimeVue
- **Backend:** FastAPI (Python 3.11)

### Flujo de Procesamiento

1. **Ingesta:** Archivo dividido en chunks de 1MB
2. **Almacenamiento:** Chunks en MongoDB, tracking en PostgreSQL
3. **Procesamiento:** Workers paralelos detectan anomalías
4. **Enriquecimiento:** Embeddings generados y almacenados en Qdrant
5. **Explicación:** LLM genera explicaciones educativas
6. **Visualización:** Frontend muestra resultados con contexto

---

## 🏗️ Arquitectura Actual

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        NGINX (Gateway)                       │
│                    Puerto 80 (HTTP)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐  ┌─────▼──────┐  ┌────▼─────┐
│   Frontend   │  │   Python   │  │  Ollama  │
│   (Vue 3)   │  │  Backend   │  │  (LLM)   │
│   Puerto 80  │  │ Puerto 8000│  │Puerto 11434│
└──────────────┘  └─────┬──────┘  └─────┬─────┘
                        │               │
        ┌───────────────┼───────────────┼───────────────┐
        │               │               │               │
┌───────▼──────┐  ┌─────▼──────┐  ┌────▼─────┐  ┌────▼─────┐
│  PostgreSQL  │  │   MongoDB   │  │  Qdrant  │  │  Redis   │
│  (Metadatos) │  │  (Logs)     │  │(Vectores)│  │ (Cache)  │
│  Puerto 5432 │  │ Puerto 27017│  │Puerto 6333│ │Puerto 6379│
└──────────────┘  └─────────────┘  └───────────┘  └───────────┘
```

### Servicios Docker

| Servicio | Imagen | Puerto | Propósito |
|----------|--------|--------|-----------|
| `frontend` | Vue 3 | 80 (Nginx) | Interfaz de usuario |
| `backend-python` | FastAPI | 8000 | Análisis y detección |
| `ollama-service` | Ollama | 11434 | Modelos LLM |
| `postgres` | PostgreSQL 15 | 5432 | Metadatos y RBAC |
| `mongodb` | MongoDB 7.0 | 27017 | Logs masivos |
| `redis` | Redis 7 | 6379 | Cache y colas |
| `qdrant` | Qdrant | 6333 | Búsqueda vectorial |
| `nginx` | Nginx | 80 | Reverse proxy |

### Bases de Datos

#### MongoDB (Logs Masivos)
- **Colecciones:**
  - `chunks`: Fragmentos de logs (1MB cada uno)
  - `results`: Resultados de análisis
  - `patterns`: Patrones detectados
- **Índices:** `file_id`, `chunk_number`, `processed`

#### PostgreSQL (Metadatos y RBAC)
- **Tablas principales:**
  - `processing_jobs`: Control de trabajos de procesamiento
  - `processing_stats`: Estadísticas de procesamiento
  - `users`: Usuarios del sistema
  - `workspaces`: Espacios de trabajo
  - `projects`: Proyectos (hijos de workspaces)
  - `roles`, `permissions`, `modules`: Sistema RBAC
- **Índices:** Optimizados para consultas frecuentes

#### Redis (Cache y Colas)
- **Estructuras:**
  - `processing:job:{id}:status`: Estado de jobs
  - `processing:job:{id}:progress`: Progreso
  - `queue:chunks_to_process`: Cola de chunks
  - `cache:pattern:{hash}`: Cache de patrones

#### Qdrant (Búsqueda Vectorial)
- **Colecciones:**
  - `normal_logs`: Logs normales (embeddings)
  - `anomalies`: Anomalías detectadas (embeddings)
- **Modelo:** `all-MiniLM-L6-v2` (384 dimensiones)
- **Distancia:** Cosine similarity

---

## 🏛️ Arquitectura Propuesta: Backends Separados

### Decisión Arquitectónica

**Separar en dos backends especializados:**
- **NestJS Backend:** Servicios de usuario, autenticación, RBAC
- **Python Backend:** Análisis de logs, detección de anomalías, ML/AI

### Justificación

1. **Separación de responsabilidades:** Cada backend hace lo que mejor sabe hacer
2. **Tecnología adecuada:** NestJS para APIs RESTful, Python para ML/AI
3. **Escalabilidad independiente:** Escalar cada backend según necesidad
4. **Desarrollo paralelo:** Equipos pueden trabajar simultáneamente
5. **Migraciones versionadas:** TypeORM (NestJS) y Alembic (Python)

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                        NGINX (Gateway)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐  ┌─────▼──────┐  ┌────▼─────┐
│   Frontend   │  │   NestJS   │  │  Python  │
│   (Vue 3)   │  │  Backend   │  │  Backend  │
│             │  │ (Usuario/  │  │ (Análisis)│
│             │  │   RBAC)    │  │           │
└──────────────┘  └─────┬──────┘  └─────┬─────┘
                        │               │
        ┌───────────────┼───────────────┼───────────────┐
        │               │               │               │
┌───────▼──────┐  ┌─────▼──────┐  ┌────▼─────┐  ┌────▼─────┐
│  PostgreSQL  │  │   MongoDB   │  │  Qdrant  │  │  Redis   │
│  (RBAC +    │  │  (Logs +    │  │(Embeddings│  │ (Cache)  │
│   Metadata) │  │  Results)   │  │           │  │          │
└──────────────┘  └─────────────┘  └───────────┘  └───────────┘
```

### Separación de Responsabilidades

#### NestJS Backend (Puerto 3001)
- ✅ Autenticación y autorización (JWT)
- ✅ Gestión de usuarios
- ✅ RBAC (Workspaces, Projects, Roles, Permissions)
- ✅ CRUD de workspaces y proyectos
- ✅ Asignación de roles
- ✅ Gestión de sesiones

**Endpoints:**
```
/api/auth/*          - Autenticación
/api/users/*         - Gestión de usuarios
/api/workspaces/*    - Gestión de workspaces
/api/projects/*      - Gestión de proyectos
/api/roles/*         - Gestión de roles
/api/permissions/*   - Verificación de permisos
```

#### Python Backend (Puerto 8000)
- ✅ Procesamiento de logs
- ✅ Detección de anomalías (Isolation Forest)
- ✅ Generación de embeddings (Qdrant)
- ✅ Explicaciones LLM (Ollama)
- ✅ Análisis y correlación temporal
- ✅ Generación de reportes

**Endpoints:**
```
/api/analyze/*       - Procesamiento de logs
/api/jobs/*          - Gestión de jobs
/api/anomalies/*     - Anomalías detectadas
/api/reports/*       - Reportes
/api/context/*       - Contexto educativo
```

### Flujo de Autenticación

1. **Usuario hace login:**
   ```
   Frontend → NestJS Backend → /api/auth/login
   NestJS valida credenciales → Genera JWT
   Retorna JWT al Frontend
   ```

2. **Frontend hace request a Python Backend:**
   ```
   Frontend → Python Backend → /api/analyze/process
   Headers: Authorization: Bearer <JWT>
   Python Backend → Lee user_id del JWT
   Python Backend → Consulta PostgreSQL para verificar permisos
   Python Backend → Procesa request si tiene permisos
   ```

### Modelo de Datos Compartido

**NestJS escribe:**
- `users`, `workspaces`, `projects`
- `roles`, `permissions`, `modules`
- `user_workspace_roles`, `user_project_roles`

**Python lee:**
- `workspaces`, `projects` (solo lectura)
- `user_workspace_roles`, `user_project_roles` (solo lectura)
- Funciones helper SQL para permisos

**Python escribe:**
- `processing_jobs` (con `workspace_id`, `project_id`)
- `processing_stats`

### Sistema de Migraciones

#### NestJS (TypeORM Migrations)
```
data/backend-nestjs/
├── src/
│   ├── migrations/
│   │   ├── 001_create_users.ts
│   │   ├── 002_create_workspaces.ts
│   │   ├── 003_create_projects.ts
│   │   └── 004_create_rbac_tables.ts
```

**Comandos:**
```bash
npm run migration:generate -- -n CreateWorkspaces
npm run migration:run
npm run migration:revert
```

#### Python (Alembic Migrations)
```
data/backend-python/
├── alembic/
│   ├── versions/
│   │   ├── 001_add_workspace_project_to_jobs.py
│   └── env.py
```

**Comandos:**
```bash
alembic revision --autogenerate -m "Add workspace_id to jobs"
alembic upgrade head
alembic downgrade -1
```

---

## 🔐 Sistema RBAC

### Estructura Jerárquica

```
Organización (Nivel Global - Implícito, manejado por Super Admin)
└── Workspace (Nivel Superior)
    ├── Project (Nivel Intermedio - Hijo de Workspace)
    │   ├── Processing Job (Nivel Inferior - Asociado a Project)
    │   └── Anomaly (Nivel Inferior - Asociado a Project)
    └── Project (Otro Proyecto)
```

### Roles del Sistema

| Rol | Descripción | Alcance |
|-----|-------------|---------|
| **super_admin** | Administrador del sistema | Acceso completo a todo |
| **workspace_admin** | Administrador de workspace | Acceso completo dentro del workspace |
| **project_admin** | Administrador de proyecto | Acceso completo dentro del proyecto |
| **analyst** | Analista | Lectura y escritura limitada |
| **viewer** | Solo lectura | Sin permisos de escritura |

### Módulos y Permisos

**Módulos:**
1. `logs`: Gestión de logs y procesamiento
2. `projects`: Gestión de proyectos
3. `workspaces`: Gestión de workspaces
4. `anomalies`: Visualización y análisis de anomalías
5. `reports`: Generación y visualización de reportes
6. `settings`: Configuración del sistema

**Acciones por módulo:**
- `read`: Ver/leer recursos
- `write`: Crear/editar recursos
- `delete`: Eliminar recursos
- `process`: Procesar logs (módulo logs)
- `feedback`: Enviar feedback (módulo anomalies)
- `admin`: Administración completa (solo algunos módulos)

### Matriz de Permisos

| Módulo | Acción | super_admin | workspace_admin | project_admin | analyst | viewer |
|--------|--------|-------------|-----------------|---------------|---------|--------|
| **logs** | read | ✅ | ✅ | ✅ | ✅ | ✅ |
| **logs** | process | ✅ | ✅ | ✅ | ✅ | ❌ |
| **projects** | read | ✅ | ✅ | ✅ | ✅ | ✅ |
| **projects** | write | ✅ | ✅ | ✅ | ❌ | ❌ |
| **workspaces** | read | ✅ | ✅ | ❌ | ✅ | ✅ |
| **workspaces** | write | ✅ | ✅ | ❌ | ❌ | ❌ |
| **anomalies** | read | ✅ | ✅ | ✅ | ✅ | ✅ |
| **anomalies** | feedback | ✅ | ✅ | ✅ | ✅ | ❌ |

### Asignación de Roles

**Nivel Workspace:**
- Tabla: `user_workspace_roles`
- Un usuario puede tener un rol en un workspace específico
- Los permisos del workspace se aplican a todos los proyectos dentro del workspace (a menos que haya un rol específico en el proyecto)

**Nivel Proyecto:**
- Tabla: `user_project_roles`
- Un usuario puede tener un rol específico en un proyecto
- Si un usuario tiene rol en proyecto, ese rol tiene prioridad sobre el rol del workspace

### Verificación de Permisos

**Funciones Helper en PostgreSQL:**

1. `check_user_workspace_permission(user_id, workspace_id, module, action)`
   - Verifica si un usuario tiene un permiso específico en un workspace
   - Si es super_admin → ✅ true
   - Busca en `user_workspace_roles` → verifica permisos del rol

2. `check_user_project_permission(user_id, project_id, module, action)`
   - Verifica si un usuario tiene un permiso específico en un proyecto
   - Si es super_admin → ✅ true
   - Busca en `user_project_roles` → verifica permisos del rol
   - Si no tiene rol en proyecto → hereda del workspace

### Endpoints Propuestos

**Workspaces:**
- `GET /api/workspaces` - Listar workspaces accesibles
- `POST /api/workspaces` - Crear workspace (requiere `workspaces:write`)
- `GET /api/workspaces/{workspace_id}` - Ver workspace
- `PUT /api/workspaces/{workspace_id}` - Editar workspace
- `DELETE /api/workspaces/{workspace_id}` - Eliminar workspace

**Projects:**
- `GET /api/workspaces/{workspace_id}/projects` - Listar proyectos
- `POST /api/workspaces/{workspace_id}/projects` - Crear proyecto
- `GET /api/projects/{project_id}` - Ver proyecto
- `PUT /api/projects/{project_id}` - Editar proyecto
- `DELETE /api/projects/{project_id}` - Eliminar proyecto

**Processing Jobs (actualizados):**
- `POST /api/projects/{project_id}/process` - Procesar log (requiere `logs:process`)
- `GET /api/projects/{project_id}/jobs` - Listar jobs (requiere `logs:read`)
- `GET /api/projects/{project_id}/jobs/{job_id}` - Ver job

**Anomalies (actualizados):**
- `GET /api/projects/{project_id}/anomalies` - Listar anomalías (requiere `anomalies:read`)
- `POST /api/projects/{project_id}/anomalies/{anomaly_id}/feedback` - Feedback (requiere `anomalies:feedback`)

---

## 🎓 Enfoque Educativo

### Principio Fundamental

**"No competir con herramientas de detección avanzadas, sino ayudar a analistas a entender mejor lo que encuentran"**

### Objetivos del Sistema

1. **Entender** por qué algo es anómalo
2. **Priorizar** qué revisar primero
3. **Aprender** patrones comunes y qué buscar
4. **Actuar** con pasos claros y contextualizados

### Características Educativas

#### 1. Contexto Educativo
- Mostrar logs normales similares para comparar
- Explicar diferencias específicas (longitud, entropía, palabras clave)
- Comparación visual entre normal y anómalo

#### 2. Agrupación Inteligente
- Agrupar anomalías por patrón común
- Mostrar frecuencia y severidad
- Identificar IPs involucradas y ventanas temporales

#### 3. Priorización Clara
- 🔴 CRÍTICO: Revisar AHORA (score alto + patrón nuevo + alta frecuencia)
- 🟠 ALTO: Revisar hoy (score medio-alto + patrón conocido)
- 🟡 MEDIO: Revisar esta semana (score medio + baja frecuencia)
- 🟢 BAJO: Revisar cuando haya tiempo (score bajo o patrones benignos)

#### 4. Visualizaciones Educativas
- Histograma de scores de anomalías
- Timeline interactivo de eventos
- Heatmap de patrones comunes
- Comparación visual de features (box plots)

#### 5. Explicaciones Detalladas
- ¿Qué pasó? (descripción del evento)
- ¿Por qué es anómalo? (comparación con normal)
- ¿Qué deberías hacer? (pasos accionables)
- Logs relacionados (contexto temporal)

#### 6. Correlaciones Temporales
- Timeline de eventos alrededor de la anomalía
- Identificación de eventos relacionados
- Detección de patrones temporales

#### 7. Base de Conocimiento
- Patrones aprendidos históricamente
- Casos históricos similares
- Mejores prácticas
- Ejemplos reales

#### 8. Sistema de Feedback
- Marcar anomalías como útiles/no útiles
- Agregar notas personalizadas
- Ajuste de thresholds basado en feedback
- Aprendizaje continuo

### Plan de Implementación

**Fase 1: Contexto Básico (2-3 semanas)**
- ✅ Mostrar logs normales similares
- ✅ Agrupación básica por similitud
- ✅ Priorización por severidad
- ✅ Timeline básico de eventos
- ✅ Explicación mejorada de diferencias

**Fase 2: Visualizaciones Educativas (2-3 semanas)**
- Histograma de scores
- Timeline interactivo
- Heatmap de patrones
- Comparación visual de features

**Fase 3: Herramientas de Análisis (2-3 semanas)**
- Filtros avanzados
- Búsqueda inteligente
- Agrupación manual
- Exportación mejorada

**Fase 4: Base de Conocimiento (3-4 semanas)**
- Base de conocimiento de patrones
- Casos históricos
- Sistema de feedback
- Guías interactivas

---

## 🔧 Implementaciones Técnicas

### Qdrant (Base de Datos Vectorial)

**Propósito:** Búsqueda de similitud de logs para comparación educativa.

**Configuración:**
- **Modelo de embeddings:** `all-MiniLM-L6-v2` (384 dimensiones)
- **Distancia:** Cosine similarity
- **Colecciones:**
  - `normal_logs`: Logs normales con embeddings
  - `anomalies`: Anomalías detectadas con embeddings

**Servicios:**
- `services/embedding_service.py`: Generación de embeddings
- `services/qdrant_service.py`: Operaciones con Qdrant

**Funciones principales:**
- `store_normal_logs()`: Almacenar logs normales
- `store_anomaly()`: Almacenar anomalías
- `find_similar_normal_logs()`: Buscar logs normales similares
- `find_similar_anomalies()`: Buscar anomalías similares para agrupación

**Uso previsto:**
1. Durante procesamiento: Almacenar logs normales y anomalías en Qdrant
2. Al mostrar anomalía: Buscar logs normales similares para comparación
3. Para agrupación: Buscar anomalías similares para agrupar automáticamente

### Detección de Anomalías

**Algoritmo:** Isolation Forest (scikit-learn)

**Features extraídas:**
- Longitud del log
- Entropía de caracteres
- Palabras clave sospechosas
- Patrones regex comunes
- Frecuencia de caracteres especiales

**Configuración:**
```python
isolation_forest = IsolationForest(
    contamination=0.1,  # 10% de anomalías esperadas
    random_state=42,
    n_estimators=100
)
```

### Procesamiento de Logs

**Chunking:**
- Tamaño: 1MB por chunk
- Respeto de líneas de log
- Procesamiento incremental

**Workers:**
- 4-8 workers paralelos
- Balanceo automático de carga
- Recuperación de errores

**Streaming:**
- Progreso en tiempo real
- Resultados incrementales
- Cancelación segura

---

## 💻 Stack Tecnológico

### Frontend
- **Framework:** Vue 3 + TypeScript
- **UI Library:** PrimeVue 3.40.0
- **Build Tool:** Vite
- **State Management:** Pinia
- **HTTP Client:** Axios

### Backend Python (Actual)
- **Framework:** FastAPI 0.104.1
- **ASGI Server:** Uvicorn 0.24.0
- **ML Library:** scikit-learn 1.3.2
- **Data Processing:** pandas 2.1.4, numpy 1.25.2
- **Database:** asyncpg 0.29.0, pymongo 4.6.1, redis 5.0.1
- **Vector DB:** qdrant-client 1.7.0
- **Embeddings:** sentence-transformers 2.2.2
- **Migrations:** alembic 1.13.1

### Backend NestJS (Propuesto)
- **Framework:** NestJS
- **ORM:** TypeORM
- **Migrations:** TypeORM Migrations
- **Auth:** Passport.js + JWT
- **Database:** PostgreSQL (asyncpg)

### Bases de Datos
- **MongoDB:** 7.0 (logs masivos)
- **PostgreSQL:** 15 (metadatos y RBAC)
- **Redis:** 7 (cache y colas)
- **Qdrant:** latest (búsqueda vectorial)

### IA/ML
- **LLM Service:** Ollama
- **Modelo por defecto:** qwen2.5:3b
- **Embeddings:** all-MiniLM-L6-v2 (384 dims)

### Infraestructura
- **Containerization:** Docker + Docker Compose
- **Reverse Proxy:** Nginx
- **OS:** Linux (recomendado), Windows/Mac (soportado)

---

## 📁 Estructura del Proyecto

```
logsanomaly/
├── build/                          # Dockerfiles y configuraciones
│   ├── backend-python/
│   │   └── Dockerfile
│   ├── backend-nestjs/             # Nuevo (propuesto)
│   │   └── Dockerfile
│   ├── ollama/
│   │   ├── Dockerfile
│   │   └── init-ollama.sh
│   ├── ui/
│   │   └── Dockerfile
│   └── mongodb/
│       └── init-mongo.js
│
├── data/                           # Código de la aplicación
│   ├── backend-python/             # Backend Python (Análisis)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── alembic/                # Migraciones Alembic
│   │   ├── services/
│   │   │   ├── embedding_service.py
│   │   │   ├── qdrant_service.py
│   │   │   └── permission_service.py
│   │   ├── models/
│   │   │   └── rbac_models.py
│   │   └── config/
│   │
│   ├── backend-nestjs/            # Backend NestJS (Usuario/RBAC) - Propuesto
│   │   ├── src/
│   │   │   ├── auth/
│   │   │   ├── users/
│   │   │   ├── workspaces/
│   │   │   ├── projects/
│   │   │   ├── roles/
│   │   │   ├── permissions/
│   │   │   └── migrations/         # Migraciones TypeORM
│   │   └── package.json
│   │
│   └── frontend/                   # Frontend Vue 3
│       ├── package.json
│       ├── src/
│       │   ├── components/
│       │   ├── stores/
│       │   └── utils/
│       └── dist/
│
├── db/                             # Scripts de bases de datos
│   ├── init.sql                    # PostgreSQL inicial
│   ├── init_rbac.sql              # RBAC schema
│   └── init-mongo.js              # MongoDB inicial
│
├── doc/                            # Documentación
│   └── DOCUMENTACION-MAESTRA.md   # Este archivo
│
├── server/                         # Configuraciones de servidor
│   └── nginx/
│       ├── nginx.conf
│       ├── conf.d/
│       └── includes/
│
├── docker-compose.yml              # Orquestación de servicios
├── env.template                    # Template de variables de entorno
└── README.md                       # Documentación principal
```

---

## 📋 Tareas y Roadmap

### ✅ Completado

- [x] Arquitectura multi-DB (MongoDB, PostgreSQL, Redis)
- [x] Sistema de chunks para archivos grandes
- [x] Procesamiento paralelo con workers
- [x] Integración de Qdrant para búsqueda vectorial
- [x] Servicios de embeddings y Qdrant
- [x] Esquema RBAC en PostgreSQL
- [x] Modelos Pydantic para RBAC
- [x] Servicio de permisos básico

### 🔄 En Progreso

- [ ] Migración a backends separados (NestJS + Python)
- [ ] Implementación de autenticación JWT
- [ ] Endpoints de workspaces y proyectos
- [ ] Integración de Qdrant en procesamiento
- [ ] Endpoints de contexto educativo

### 📋 Pendiente

#### Fase 1: Backend NestJS (2-3 semanas)
- [ ] Crear estructura básica de NestJS
- [ ] Configurar TypeORM y PostgreSQL
- [ ] Crear migraciones TypeORM para RBAC
- [ ] Implementar autenticación JWT
- [ ] Crear módulos de usuarios, workspaces, proyectos
- [ ] Implementar sistema de permisos
- [ ] Crear endpoints de gestión

#### Fase 2: Integración Python (1 semana)
- [ ] Actualizar Python para leer permisos de PostgreSQL
- [ ] Implementar middleware de autenticación en Python
- [ ] Actualizar endpoints para verificar permisos
- [ ] Configurar Nginx para routing correcto

#### Fase 3: Migraciones Alembic (3-5 días)
- [ ] Configurar Alembic en Python
- [ ] Crear migraciones para cambios existentes
- [ ] Migrar `processing_jobs` para incluir `workspace_id` y `project_id`

#### Fase 4: Enfoque Educativo (4-8 semanas)
- [ ] Integrar almacenamiento de logs normales en Qdrant
- [ ] Integrar almacenamiento de anomalías en Qdrant
- [ ] Crear endpoints de contexto educativo
- [ ] Implementar agrupación inteligente
- [ ] Crear visualizaciones educativas
- [ ] Implementar sistema de feedback
- [ ] Crear base de conocimiento de patrones

---

## 🔗 Referencias Técnicas

### Documentación Externa

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [NestJS Documentation](https://docs.nestjs.com/)
- [TypeORM Migrations](https://typeorm.io/migrations)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Sentence Transformers](https://www.sbert.net/)
- [Ollama Documentation](https://ollama.ai/docs)

### Archivos de Referencia en el Proyecto

- `db/init_rbac.sql` - Esquema completo de RBAC
- `data/backend-python/models/rbac_models.py` - Modelos Pydantic
- `data/backend-python/services/permission_service.py` - Servicio de permisos
- `data/backend-python/services/qdrant_service.py` - Servicio Qdrant
- `data/backend-python/services/embedding_service.py` - Servicio de embeddings
- `docker-compose.yml` - Configuración de servicios
- `env.template` - Variables de entorno

### Decisiones Arquitectónicas Documentadas

1. **Separación de backends:** Ver sección "Arquitectura Propuesta"
2. **Sistema RBAC:** Ver sección "Sistema RBAC"
3. **Enfoque educativo:** Ver sección "Enfoque Educativo"
4. **Qdrant para similitud:** Ver sección "Implementaciones Técnicas"

---

## 📝 Notas para Desarrolladores

### Convenciones de Código

- **Python:** PEP 8, type hints, async/await para operaciones I/O
- **TypeScript:** ESLint, strict mode, interfaces explícitas
- **SQL:** Funciones helper para permisos, índices optimizados

### Flujo de Desarrollo

1. **Crear migraciones** antes de cambios de esquema
2. **Verificar permisos** en todos los endpoints protegidos
3. **Usar servicios** en lugar de acceso directo a DB
4. **Documentar decisiones** arquitectónicas importantes

### Testing

- **Backend Python:** pytest, async tests para endpoints
- **Backend NestJS:** Jest, tests unitarios y de integración
- **Frontend:** Vitest, tests de componentes Vue

### Deployment

- **Desarrollo:** `docker-compose up`
- **Producción:** `docker-compose -f docker-compose.prod.yml up -d`
- **Migraciones:** Ejecutar antes de iniciar servicios

---

**Última actualización:** 18 de diciembre de 2025  
**Mantenido por:** Equipo LogsAnomaly  
**Versión del documento:** 2.0.0

