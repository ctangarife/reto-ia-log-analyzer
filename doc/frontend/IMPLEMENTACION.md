# Implementación Frontend - Log Anomaly Detector

## Resumen

Implementación completa del frontend en Vue 3 con TypeScript, siguiendo la arquitectura definida en `GUIA-DESARROLLADOR-FRONTEND.md`.

## Arquitectura Implementada

### Stack Tecnológico

- **Vue 3** con Composition API
- **TypeScript** para tipado estático
- **Pinia** para gestión de estado
- **PrimeVue** para componentes UI
- **Axios** para peticiones HTTP
- **Vue Router** para navegación (preparado para futuras expansiones)

### Estructura de Carpetas

```
data/frontend/
├── src/
│   ├── components/          # Componentes Vue
│   │   ├── Login.vue        # Componente de autenticación
│   │   ├── ProcessingV2.vue # Procesamiento de logs V2
│   │   ├── AnalysisHistory.vue # Historial de análisis
│   │   └── MonitoringDashboard.vue # Dashboard de monitoreo
│   ├── stores/             # Stores de Pinia
│   │   ├── authStore.ts     # Autenticación y permisos
│   │   └── analysisStore.ts # Análisis y reportes
│   ├── services/            # Servicios de API
│   │   ├── api.ts          # Cliente HTTP con interceptores
│   │   └── authService.ts  # Servicio de autenticación
│   ├── utils/              # Utilidades
│   │   ├── jwt.ts         # Utilidades JWT
│   │   └── permissions.ts # Helpers de permisos
│   ├── App.vue            # Componente raíz
│   └── main.ts            # Punto de entrada
├── package.json
└── vite.config.ts
```

## Funcionalidades Implementadas

### 1. Autenticación

- ✅ Login con username/password
- ✅ Almacenamiento de JWT en localStorage
- ✅ Decodificación de JWT para extraer `user_id` y `is_super_admin`
- ✅ Interceptores de Axios para incluir token en todas las peticiones
- ✅ Manejo de expiración de token y redirección al login
- ✅ Logout

### 2. Sistema de Permisos RBAC

- ✅ Carga de workspaces accesibles al iniciar sesión
- ✅ Carga de proyectos accesibles por workspace
- ✅ Carga de permisos específicos por proyecto
- ✅ Store de permisos con funciones helper:
  - `hasPermission(module, action, projectId)`
  - `canProcessLogs(projectId)`
  - `canViewReports(projectId)`
  - `canAccessMonitoring()`
- ✅ Verificación de permisos antes de mostrar acciones
- ✅ Ocultación de elementos UI según permisos
- ✅ Soporte para super administrador

### 3. Procesamiento de Logs

- ✅ Selector de workspace y proyecto
- ✅ Verificación de `logs:write` antes de habilitar procesamiento
- ✅ Upload de archivo con FormData
- ✅ Manejo de respuesta `/api/process` y guardado de `job_id`
- ✅ Polling de estado con `/api/status/{job_id}` cada 2-3 segundos
- ✅ Streaming de resultados con `/api/results/{job_id}/stream` (SSE vía RabbitMQ)
  - Consumo de eventos SSE desde RabbitMQ
  - Manejo de reconexión automática (los mensajes no se pierden gracias a RabbitMQ)
  - Acumulación de anomalías en tiempo real
- ✅ Cancelación de jobs con `/api/cancel/{job_id}`
- ✅ Manejo de errores 409 (conflicto), 403 (permisos), 400 (bad request)

### 4. Visualización de Reportes

- ✅ Carga de reportes con `/api/reports`
- ✅ Filtrado por proyecto/workspace según permisos
- ✅ Visualización de detalles de reportes
- ✅ Verificación de `logs:read` antes de mostrar detalles
- ✅ Paginación preparada (backend ya filtra)

### 5. Dashboard de Monitoreo

- ✅ Verificación de `monitoring:read` antes de mostrar dashboard
- ✅ Actualización periódica cada 30 segundos
- ✅ Visualización de métricas del sistema
- ✅ Alertas destacadas
- ✅ Gráficos de memoria y CPU

### 6. Manejo de Errores

- ✅ Manejo de `401 Unauthorized` (redirigir al login)
- ✅ Manejo de `403 Forbidden` (mostrar mensaje de permisos)
- ✅ Manejo de `409 Conflict` (archivo ya procesándose)
- ✅ Manejo de `500 Internal Server Error` (mensaje genérico)
- ✅ Mensajes de error amigables para el usuario

## Componentes Principales

### Login.vue

Componente de autenticación que:
- Muestra formulario de login
- Valida credenciales
- Almacena JWT
- Redirige a la aplicación principal

### App.vue

Componente raíz que:
- Verifica autenticación al cargar
- Muestra selectores de workspace/proyecto
- Protege rutas según permisos
- Maneja navegación entre tabs

### ProcessingV2.vue

Componente de procesamiento que:
- Muestra selector de proyecto (solo con `logs:write`)
- Maneja upload de archivo
- Muestra progreso en tiempo real
- Implementa streaming SSE
- Permite cancelar procesamiento

### AnalysisHistory.vue

Componente de historial que:
- Carga reportes desde `/api/reports`
- Filtra por proyecto/workspace
- Muestra resumen de análisis
- Permite seleccionar análisis para ver detalles

### MonitoringDashboard.vue

Componente de monitoreo que:
- Verifica permiso `monitoring:read`
- Actualiza datos cada 30 segundos
- Muestra métricas del sistema
- Visualiza alertas

## Stores

### authStore.ts

Store de autenticación que gestiona:
- Token JWT
- Información del usuario
- Workspaces accesibles
- Proyectos accesibles
- Permisos por proyecto
- Funciones helper de verificación

### analysisStore.ts

Store de análisis que gestiona:
- Historial de análisis
- Análisis actual
- Jobs de procesamiento
- Streaming de resultados
- Estado de carga

## Servicios

### api.ts

Cliente HTTP con:
- Interceptor para agregar token JWT
- Interceptor para manejar errores 401/403
- Configuración base de Axios

### authService.ts

Servicio de autenticación con:
- Login
- Logout
- Verificación de token
- Decodificación de JWT

## Utilidades

### jwt.ts

Funciones para:
- Decodificar JWT
- Extraer `user_id`
- Verificar `is_super_admin`
- Verificar expiración

### permissions.ts

Funciones helper para:
- Verificar permisos específicos
- Verificar acceso a recursos
- Filtrar recursos según permisos

## Flujo de Autenticación

1. Usuario accede a la aplicación
2. Si no hay token, redirige a `/login`
3. Usuario ingresa credenciales
4. Backend valida y retorna JWT
5. Frontend almacena JWT y decodifica
6. Frontend carga workspaces/proyectos accesibles
7. Frontend carga permisos por proyecto
8. Usuario puede usar la aplicación según permisos

## Flujo de Procesamiento

1. Usuario selecciona workspace y proyecto
2. Frontend verifica `logs:write` en proyecto seleccionado
3. Si tiene permiso, habilita botón "Procesar"
4. Usuario selecciona archivo y hace clic en "Procesar"
5. Frontend envía archivo a `/api/process`
6. Backend retorna `job_id`
7. Frontend inicia polling de estado cada 2-3 segundos
8. Frontend inicia streaming SSE para resultados en tiempo real
9. Frontend actualiza UI con progreso y anomalías
10. Cuando completa, carga reportes actualizados

## Seguridad

- ✅ Token JWT almacenado en localStorage (considerar httpOnly cookies en producción)
- ✅ Verificación de permisos en frontend (pre-verificación UX)
- ✅ Backend siempre verifica permisos (seguridad real)
- ✅ Manejo de tokens expirados
- ✅ Redirección automática al login si no autenticado

## Arquitectura de Streaming SSE con RabbitMQ

El sistema usa **RabbitMQ** para el streaming SSE (no Redis Pub/Sub) porque ofrece:
- **Persistencia**: Si el cliente se desconecta, puede reconectarse y recibir mensajes perdidos
- **Garantías de entrega**: Los mensajes se entregan de forma confiable
- **Escalabilidad**: Múltiples clientes pueden escuchar el mismo job eficientemente

**Cómo Funciona**:
1. El backend crea una cola RabbitMQ dedicada para cada job: `job.{job_id}.stream`
2. Los workers publican actualizaciones a un Exchange RabbitMQ
3. El Exchange distribuye mensajes a la cola del job
4. El endpoint SSE consume mensajes de la cola y los formatea como SSE
5. Si te desconectas, los mensajes quedan en cola y se entregan al reconectar

**Implementación Frontend**:
- El frontend usa `fetch` con `response.body.getReader()` para consumir el stream SSE
- Maneja reconexión automática si la conexión se pierde
- Gracias a RabbitMQ, no necesita polling adicional para recuperar mensajes perdidos
- Los mensajes se acumulan y se muestran en tiempo real

Ver `doc/GUIA-DESARROLLADOR-FRONTEND.md` sección "Arquitectura de Streaming" y `doc/ARQUITECTURA-RABBITMQ.md` para más detalles.

## Próximos Pasos

Ver `ESTADO-ACTUAL.md` para detalles de mejoras futuras y tareas pendientes.
