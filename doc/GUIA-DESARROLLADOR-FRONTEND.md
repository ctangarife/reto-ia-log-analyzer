# Guía para Desarrolladores Frontend

> **Documentación de integración con el Backend de Anomaly Detector**
> 
> Esta guía explica cómo usar los servicios del backend, el sistema de permisos RBAC y las implementaciones necesarias para la segregación de permisos.

---

## 📋 Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Autenticación y Autorización](#autenticación-y-autorización)
3. [Sistema de Permisos RBAC](#sistema-de-permisos-rbac)
4. [Endpoints de Procesamiento](#endpoints-de-procesamiento)
5. [Endpoints de Monitoreo](#endpoints-de-monitoreo)
6. [Manejo de Errores](#manejo-de-errores)
7. [Implementación de Segregación de Permisos](#implementación-de-segregación-de-permisos)

**Implementación de Workspaces (nuevos endpoints)**: Ver **[doc/frontend/IMPLEMENTACION-WORKSPACES.md](frontend/IMPLEMENTACION-WORKSPACES.md)** para guía detallada de integración de `GET/POST/PUT/DELETE /api/workspaces` en el frontend.

---

## 🏗️ Arquitectura General

### Flujo de Datos

El sistema funciona con una arquitectura multi-DB donde cada componente tiene una responsabilidad específica:

1. **Frontend** envía peticiones al backend a través de Nginx (puerto 80)
2. **Backend Python** procesa los logs usando Isolation Forest y genera explicaciones con Ollama Cloud
3. **Bases de Datos** almacenan diferentes tipos de información:
   - **PostgreSQL**: Metadatos, jobs de procesamiento, usuarios, workspaces, proyectos, roles y permisos
   - **MongoDB**: Chunks de logs y resultados de análisis
   - **Redis**: Cache y Pub/Sub para streaming en tiempo real
   - **Qdrant**: Embeddings vectoriales para búsqueda de similitud

### Base URL

Todas las peticiones deben ir a `/api/*` desde el frontend. Nginx hace el rewrite automáticamente al backend interno.

**Ejemplo**: `/api/process` → Backend procesa en `/process`

---

## 🔐 Autenticación y Autorización

### Concepto de Autenticación

El sistema usa **JWT (JSON Web Tokens)** para autenticación. Cada usuario debe autenticarse y recibir un token que debe incluirse en todas las peticiones subsiguientes.

### Flujo de Autenticación

1. **Login**: El usuario envía credenciales (username/password)
2. **Token**: El backend valida y retorna un JWT con información del usuario
3. **Peticiones**: Todas las peticiones incluyen el token en el header `Authorization: Bearer <token>`
4. **Validación**: El backend extrae el `user_id` del token y verifica permisos antes de procesar

### Header Requerido

Todas las peticiones (excepto `/health` y login) deben incluir:

```
Authorization: Bearer <jwt_token>
```

### Estructura del Token

El token JWT contiene:
- `user_id`: Identificador único del usuario (UUID)
- `username`: Nombre de usuario
- `exp`: Fecha de expiración
- Otros claims según necesidad

**Importante**: El frontend debe extraer el `user_id` del token decodificado para usarlo en verificaciones de permisos.

---

## 🛡️ Sistema de Permisos RBAC

### Concepto de RBAC

El sistema usa **Role-Based Access Control (RBAC)** con una jerarquía de tres niveles:

1. **Workspaces** (Espacios de trabajo)
   - Contenedor de nivel superior
   - Agrupa proyectos relacionados
   - Ejemplo: "Departamento de IT", "Equipo de Seguridad"

2. **Projects** (Proyectos)
   - Pertenece a un workspace
   - Agrupa jobs de procesamiento
   - Ejemplo: "Análisis de logs de producción", "Monitoreo de seguridad"

3. **Roles** (Roles)
   - Se asignan a usuarios en workspaces o proyectos
   - Definen qué puede hacer el usuario
   - Ejemplo: "Admin", "Analista", "Solo Lectura"

### Jerarquía de Permisos

```
Workspace
  └── Project 1
      └── Job 1 (procesamiento de logs)
      └── Job 2
  └── Project 2
      └── Job 3
```

**Regla importante**: Un usuario debe tener acceso al **workspace** y al **project** para poder procesar logs en ese proyecto.

### Módulos y Acciones

El sistema define permisos por **módulo** y **acción**:

#### Módulos Disponibles
- `logs`: Procesamiento y gestión de logs
- `projects`: Gestión de proyectos
- `workspaces`: Gestión de workspaces
- `anomalies`: Visualización y gestión de anomalías
- `users`: Gestión de usuarios (solo admins)
- `monitoring`: Acceso al dashboard de monitoreo

#### Acciones Disponibles
- `read`: Ver/leer recursos
- `write`: Crear/modificar recursos
- `delete`: Eliminar recursos
- `admin`: Acceso completo (incluye todas las acciones)

### Ejemplos de Permisos

- `logs:read` → Puede ver reportes y resultados
- `logs:write` → Puede procesar nuevos archivos de logs
- `projects:admin` → Puede gestionar completamente un proyecto
- `anomalies:read` → Puede ver anomalías detectadas

### Super Administrador

Los usuarios con `is_super_admin: true` tienen acceso completo a todo el sistema, sin necesidad de verificar permisos específicos.

---

## 📡 Endpoints de Procesamiento

### POST `/api/process`

**Propósito**: Iniciar el procesamiento de un archivo de logs.

**Permiso Requerido**: `logs:write` en el proyecto especificado.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Payload**:
- `file`: Archivo de logs (FormData)
- `project_id`: (Opcional) UUID del proyecto. Si no se envía, se usa el proyecto por defecto del usuario.

**Respuesta Exitosa (200)**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Procesamiento iniciado",
  "total_chunks": 15,
  "estimated_time": 120
}
```

**Comportamiento**:
- El backend divide el archivo en chunks de 1MB
- Crea un job en PostgreSQL con estado "pending"
- Inicia procesamiento asíncrono
- Retorna inmediatamente con el `job_id`
- El procesamiento continúa en segundo plano

**Implementación Frontend**:
1. Obtener `user_id` del token JWT decodificado
2. Verificar que el usuario tiene `logs:write` en el proyecto (opcional, pero recomendado)
3. Crear FormData con el archivo
4. Enviar petición POST
5. Guardar `job_id` para polling de estado
6. Iniciar streaming de resultados (opcional)

**Errores Comunes**:
- `409 Conflict`: Ya hay un archivo procesándose (solo se permite uno a la vez)
- `403 Forbidden`: Usuario no tiene permiso `logs:write`
- `400 Bad Request`: Archivo inválido o muy grande

---

### GET `/api/status/{job_id}`

**Propósito**: Obtener el estado actual de un job de procesamiento.

**Permiso Requerido**: `logs:read` en el proyecto del job.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Parámetros**:
- `job_id`: UUID del job (en la URL)

**Respuesta Exitosa (200)**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 0.65,
  "chunks_processed": 10,
  "total_chunks": 15,
  "anomalies_found": 42,
  "estimated_remaining_time": 45,
  "error_message": null
}
```

**Estados Posibles**:
- `pending`: Job creado, esperando procesamiento
- `processing`: Procesamiento en curso
- `completed`: Procesamiento completado exitosamente
- `failed`: Error durante el procesamiento
- `cancelled`: Procesamiento cancelado por el usuario

**Implementación Frontend**:
1. Polling cada 2-3 segundos mientras `status === "processing"`
2. Mostrar barra de progreso usando `progress` (0.0 a 1.0)
3. Mostrar contador de chunks: `chunks_processed / total_chunks`
4. Si `status === "completed"`, cargar reportes
5. Si `status === "failed"`, mostrar `error_message`

**Verificación de Permisos**:
- El backend verifica que el usuario tiene acceso al proyecto del job
- Si no tiene acceso, retorna `403 Forbidden`

---

### GET `/api/results/{job_id}/stream`

**Propósito**: Obtener resultados en tiempo real usando Server-Sent Events (SSE).

**Permiso Requerido**: `logs:read` en el proyecto del job.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Parámetros**:
- `job_id`: UUID del job (en la URL)

**Respuesta**: Stream de eventos SSE (text/event-stream)

**Arquitectura de Streaming**:

El sistema usa **RabbitMQ** para el streaming (no Redis Pub/Sub) porque ofrece:
- **Persistencia**: Si te desconectas, puedes reconectarte y recibir mensajes perdidos
- **Garantías de entrega**: Los mensajes se entregan de forma confiable
- **Escalabilidad**: Múltiples clientes pueden escuchar el mismo job eficientemente

**Cómo Funciona**:
1. El backend crea una cola RabbitMQ dedicada para este job: `job.{job_id}.stream`
2. Los workers publican actualizaciones a un Exchange RabbitMQ
3. El Exchange distribuye mensajes a la cola del job
4. El endpoint SSE consume mensajes de la cola y los formatea como SSE
5. Si te desconectas, los mensajes quedan en cola y se entregan al reconectar

**Formato de Eventos**:
```
data: {"type": "stream_started", "job_id": "..."}

data: {"type": "batch_progress", "chunk_number": 1, "anomalies": [...], "progress": 0.1}

data: {"type": "job_completed", "job_id": "..."}
```

**Tipos de Eventos**:
- `stream_started`: Stream iniciado
- `batch_progress`: Nuevo batch de anomalías procesado
- `chunk_progress`: Progreso de procesamiento de chunks
- `job_completed`: Job completado
- `error`: Error en el stream

**Implementación Frontend**:
1. Crear `EventSource` o usar `fetch` con streaming
2. Escuchar eventos `message`
3. Parsear JSON de cada evento `data:`
4. Actualizar UI en tiempo real con cada `batch_progress`
5. Manejar reconexión automática si la conexión se pierde
6. Cerrar conexión cuando reciba `job_completed`

**Reconexión Inteligente**:
- Si la conexión SSE se pierde, puedes reconectarte
- El backend entregará los mensajes que se perdieron durante la desconexión
- No necesitas hacer polling adicional de `/status/{job_id}` para recuperar estado

**Ejemplo de Evento batch_progress**:
```json
{
  "type": "batch_progress",
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

**Nota**: El streaming se cierra automáticamente cuando el job completa. El frontend debe manejar reconexión si la conexión se pierde, pero con RabbitMQ los mensajes no se pierden.

---

### POST `/api/cancel/{job_id}`

**Propósito**: Cancelar un job de procesamiento en curso.

**Permiso Requerido**: `logs:write` en el proyecto del job (o ser el creador del job).

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Parámetros**:
- `job_id`: UUID del job (en la URL)

**Respuesta Exitosa (200)**:
```json
{
  "message": "Procesamiento cancelado",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Comportamiento**:
- Cambia el estado del job a `cancelled`
- Detiene el procesamiento en curso
- Los chunks ya procesados se mantienen, pero no se procesan más

**Implementación Frontend**:
1. Verificar que el usuario tiene permiso antes de mostrar botón "Cancelar"
2. Confirmar acción con el usuario
3. Enviar petición POST
4. Actualizar estado del job a `cancelled`
5. Detener polling y streaming

---

### GET `/api/reports`

**Propósito**: Obtener todos los reportes completados a los que el usuario tiene acceso.

**Permiso Requerido**: `logs:read` en al menos un proyecto.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Query Parameters** (Opcionales):
- `project_id`: Filtrar por proyecto específico
- `workspace_id`: Filtrar por workspace específico
- `limit`: Número máximo de reportes (default: 50)
- `offset`: Paginación (default: 0)

**Respuesta Exitosa (200)**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-15T10:30:45Z",
    "fileName": "server_logs_2024-01-15.txt",
    "total_logs": 15000,
    "anomalies_detected": 42,
    "anomalies": [
      {
        "log_entry": "ERROR: Connection timeout",
        "score": -0.15,
        "is_anomaly": true,
        "explanation": "El servidor está experimentando timeouts...",
        "chunk_id": "chunk-uuid"
      }
    ],
    "report_file": "db_report_550e8400.json",
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "total_chunks": 15,
    "chunks_processed": 15
  }
]
```

**Comportamiento**:
- El backend filtra automáticamente los reportes según los permisos del usuario
- Solo retorna reportes de proyectos a los que el usuario tiene acceso
- Ordenados por fecha (más recientes primero)

**Implementación Frontend**:
1. Cargar reportes al inicializar la aplicación
2. Filtrar por proyecto/workspace si el usuario selecciona filtros
3. Mostrar lista de reportes con información resumida
4. Al hacer clic en un reporte, mostrar detalles completos
5. Implementar paginación si hay muchos reportes

**Verificación de Permisos**:
- El backend verifica automáticamente los permisos del usuario
- Solo retorna reportes de proyectos accesibles
- No requiere verificación adicional en el frontend

---

## 📊 Endpoints de Monitoreo

### GET `/api/monitoring/dashboard`

**Propósito**: Obtener datos completos para el dashboard de monitoreo del sistema.

**Permiso Requerido**: `monitoring:read` a nivel de workspace o ser super admin.

**Headers Requeridos**:
```
Authorization: Bearer <jwt_token>
```

**Respuesta Exitosa (200)**:
```json
{
  "current_stats": {
    "memory_usage_mb": 2048,
    "cpu_percent": 45.2,
    "active_jobs": 1,
    "total_jobs_today": 5,
    "anomalies_detected_today": 127
  },
  "history": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "memory_mb": 1980,
      "cpu_percent": 42.1
    }
  ],
  "alerts": [
    {
      "type": "high_memory",
      "message": "Uso de memoria alto: 85%",
      "severity": "warning",
      "timestamp": "2024-01-15T10:25:00Z"
    }
  ],
  "summary": {
    "status": "healthy",
    "services": {
      "mongodb": "online",
      "postgres": "online",
      "redis": "online",
      "qdrant": "online",
      "ollama": "online"
    }
  },
  "timestamp": "2024-01-15T10:30:45Z"
}
```

**Implementación Frontend**:
1. Actualizar dashboard cada 30 segundos
2. Mostrar gráficos de memoria y CPU con `history`
3. Mostrar alertas destacadas si `alerts` tiene elementos
4. Indicadores de estado de servicios con colores (verde/rojo)
5. Solo mostrar si el usuario tiene permiso `monitoring:read`

---

## ⚠️ Manejo de Errores

### Códigos de Estado HTTP

- `200 OK`: Petición exitosa
- `400 Bad Request`: Datos inválidos en la petición
- `401 Unauthorized`: Token faltante o inválido
- `403 Forbidden`: Usuario no tiene permisos necesarios
- `404 Not Found`: Recurso no encontrado (job, proyecto, etc.)
- `409 Conflict`: Conflicto (ej: ya hay un archivo procesándose)
- `500 Internal Server Error`: Error del servidor

### Estructura de Errores

Todas las respuestas de error siguen este formato:

```json
{
  "detail": "Mensaje de error descriptivo"
}
```

### Errores Comunes y Soluciones

#### 401 Unauthorized
**Causa**: Token faltante, expirado o inválido
**Solución**: 
- Verificar que el header `Authorization` está presente
- Verificar que el token no ha expirado
- Redirigir al usuario al login si el token es inválido

#### 403 Forbidden
**Causa**: Usuario no tiene el permiso necesario
**Solución**:
- Verificar permisos antes de mostrar acciones al usuario
- Mostrar mensaje claro: "No tienes permiso para realizar esta acción"
- Ocultar botones/acciones que requieren permisos que el usuario no tiene

#### 409 Conflict
**Causa**: Ya hay un archivo procesándose
**Solución**:
- Mostrar mensaje: "Ya hay un archivo en procesamiento. Espera a que termine."
- Deshabilitar botón de "Procesar" mientras hay un job activo
- Mostrar el job actual en curso

#### 500 Internal Server Error
**Causa**: Error del servidor
**Solución**:
- Mostrar mensaje genérico: "Error del servidor. Intenta más tarde."
- Loggear el error para debugging
- Ofrecer reintentar la operación

---

## 🔒 Implementación de Segregación de Permisos

### Concepto Fundamental

La **segregación de permisos** significa que cada usuario solo puede ver y realizar acciones en los recursos (workspaces, proyectos, jobs) a los que tiene acceso según sus roles y permisos asignados.

### Flujo de Verificación de Permisos

#### 1. Al Cargar la Aplicación

**Paso 1**: Obtener información del usuario desde el token JWT
- Extraer `user_id` del token decodificado
- Verificar si `is_super_admin === true`

**Paso 2**: Cargar workspaces y proyectos accesibles
- Si es super admin: Mostrar todos los workspaces/proyectos
- Si no: Solo mostrar workspaces/proyectos a los que tiene acceso

**Implementación**:
- Crear función `getUserWorkspaces(userId)` que consulta el backend
- Crear función `getUserProjects(userId, workspaceId?)` que consulta el backend
- Almacenar esta información en el store de la aplicación

#### 2. Al Mostrar Lista de Reportes

**Verificación Automática**: El backend ya filtra los reportes según permisos, pero el frontend debe:

- Mostrar solo proyectos/workspaces accesibles en filtros
- No mostrar reportes de proyectos inaccesibles (aunque el backend ya los filtra)
- Mostrar mensaje si no hay reportes: "No tienes acceso a ningún proyecto con reportes"

#### 3. Al Procesar un Archivo

**Verificación Requerida**:
1. Verificar que el usuario tiene `logs:write` en el proyecto seleccionado
2. Si no tiene permiso, mostrar mensaje y deshabilitar botón "Procesar"
3. Solo permitir seleccionar proyectos donde tiene `logs:write`

**Implementación**:
- Antes de mostrar el selector de proyectos, filtrar solo proyectos con `logs:write`
- Verificar permiso antes de enviar la petición (aunque el backend también verifica)
- Mostrar feedback claro si no tiene permisos

#### 4. Al Ver Detalles de un Reporte

**Verificación Automática**: El backend verifica permisos, pero el frontend debe:

- Solo mostrar botones de acciones si el usuario tiene los permisos necesarios
- Ocultar "Eliminar" si no tiene `logs:delete`
- Ocultar "Reprocesar" si no tiene `logs:write`

#### 5. Al Acceder al Dashboard de Monitoreo

**Verificación Requerida**:
- Verificar que el usuario tiene `monitoring:read` en al menos un workspace
- Si no tiene permiso, ocultar completamente la sección de monitoreo
- Mostrar mensaje: "No tienes acceso al dashboard de monitoreo"

### Patrón de Verificación en Frontend

#### Estructura Recomendada

1. **Store de Permisos**: Mantener en memoria los permisos del usuario
   - Workspaces accesibles
   - Proyectos accesibles con sus permisos
   - Roles asignados

2. **Funciones Helper**: Crear funciones para verificar permisos
   - `hasPermission(module, action, projectId)`: Verifica permiso específico
   - `canProcessLogs(projectId)`: Verifica `logs:write`
   - `canViewReports(projectId)`: Verifica `logs:read`
   - `canAccessMonitoring()`: Verifica `monitoring:read`

3. **Componentes Reactivos**: Los componentes deben reaccionar a cambios de permisos
   - Ocultar/mostrar elementos según permisos
   - Deshabilitar botones si no hay permisos
   - Mostrar mensajes informativos

### Ejemplo de Implementación Conceptual

#### Al Inicializar la Aplicación

1. Decodificar token JWT para obtener `user_id`
2. Consultar backend para obtener workspaces accesibles del usuario
3. Para cada workspace, consultar proyectos accesibles
4. Para cada proyecto, consultar permisos específicos del usuario
5. Almacenar toda esta información en el store

#### Al Mostrar Interfaz

1. **Selector de Workspace**: Mostrar solo workspaces accesibles
2. **Selector de Proyecto**: Mostrar solo proyectos del workspace seleccionado donde tiene acceso
3. **Botón "Procesar"**: Solo habilitado si tiene `logs:write` en el proyecto seleccionado
4. **Lista de Reportes**: El backend ya filtra, pero mostrar solo proyectos accesibles en filtros
5. **Dashboard de Monitoreo**: Solo visible si tiene `monitoring:read`

### Verificación en Tiempo Real

Aunque el backend verifica permisos en cada petición, el frontend debe:

- **Pre-verificar** antes de mostrar acciones (mejor UX)
- **Manejar errores 403** si el permiso cambió entre la verificación y la petición
- **Actualizar permisos** si el usuario cambia de workspace/proyecto

### Casos Especiales

#### Super Administrador

Si `is_super_admin === true`:
- Mostrar todos los workspaces y proyectos
- Habilitar todas las acciones
- Omitir verificaciones de permisos (aunque el backend también lo hace)

#### Usuario Sin Proyectos

Si el usuario no tiene acceso a ningún proyecto:
- Mostrar mensaje: "No tienes acceso a ningún proyecto. Contacta a un administrador."
- Ocultar funcionalidades de procesamiento
- Mostrar solo información general (si aplica)

#### Permisos Cambiantes

Si los permisos del usuario cambian durante la sesión:
- El backend rechazará peticiones con `403 Forbidden`
- El frontend debe manejar esto y actualizar la UI
- Considerar refrescar la lista de permisos periódicamente

---

## 📝 Resumen de Implementación

### Checklist para Desarrollador Frontend

#### Autenticación
- [ ] Implementar login y almacenamiento de JWT
- [ ] Decodificar JWT para extraer `user_id` y `is_super_admin`
- [ ] Incluir header `Authorization: Bearer <token>` en todas las peticiones
- [ ] Manejar expiración de token y redirigir al login

#### Carga de Permisos
- [ ] Al iniciar sesión, cargar workspaces accesibles del usuario (`GET /api/workspaces` — ver [IMPLEMENTACION-WORKSPACES.md](frontend/IMPLEMENTACION-WORKSPACES.md))
- [ ] Cargar proyectos accesibles para cada workspace
- [ ] Cargar permisos específicos para cada proyecto
- [ ] Almacenar esta información en el store

#### Verificación de Permisos
- [ ] Crear funciones helper para verificar permisos
- [ ] Verificar permisos antes de mostrar acciones
- [ ] Ocultar elementos UI si el usuario no tiene permisos
- [ ] Mostrar mensajes informativos cuando no hay permisos

#### Procesamiento de Logs
- [ ] Filtrar proyectos mostrados solo a los que tiene `logs:write`
- [ ] Verificar permiso antes de habilitar botón "Procesar"
- [ ] Manejar respuesta del endpoint `/process` y guardar `job_id`
- [ ] Implementar polling de estado con `/status/{job_id}`
- [ ] Implementar streaming con `/results/{job_id}/stream`
- [ ] Manejar cancelación con `/cancel/{job_id}`

#### Visualización de Reportes
- [ ] Cargar reportes con `/reports`
- [ ] Filtrar por proyecto/workspace según permisos
- [ ] Mostrar detalles de reportes solo si tiene `logs:read`
- [ ] Implementar paginación si hay muchos reportes

#### Monitoreo
- [ ] Verificar `monitoring:read` antes de mostrar dashboard
- [ ] Actualizar dashboard periódicamente (cada 30s)
- [ ] Mostrar alertas y métricas del sistema

#### Manejo de Errores
- [ ] Manejar `401 Unauthorized` (redirigir al login)
- [ ] Manejar `403 Forbidden` (mostrar mensaje de permisos)
- [ ] Manejar `409 Conflict` (archivo ya procesándose)
- [ ] Manejar `500 Internal Server Error` (mensaje genérico)

---

## 🎯 Mejores Prácticas

### Seguridad

1. **Nunca confiar solo en verificaciones del frontend**: El backend siempre verifica permisos
2. **No almacenar permisos sensibles en localStorage**: Solo el token JWT
3. **Validar token antes de cada petición**: Verificar que no ha expirado
4. **Manejar tokens expirados**: Redirigir al login automáticamente

### UX

1. **Pre-verificar permisos**: Mejor que mostrar errores después
2. **Mensajes claros**: Explicar por qué una acción no está disponible
3. **Feedback inmediato**: Mostrar loading states durante peticiones
4. **Manejo de errores amigable**: Mensajes claros, no técnicos

### Performance

1. **Cachear permisos**: No consultar en cada render
2. **Lazy loading**: Cargar proyectos solo cuando se selecciona workspace
3. **Debounce en polling**: No hacer polling demasiado frecuente
4. **Cerrar streams**: Cerrar conexiones SSE cuando no se necesiten

---

**Última actualización**: Migración completa a arquitectura consolidada
**Versión API**: 2.0.0
