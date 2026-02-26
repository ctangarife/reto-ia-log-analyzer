# 🐰 Arquitectura con RabbitMQ - LogsAnomaly

**Fecha:** 18 de diciembre de 2025  
**Estado:** Propuesta de diseño  
**Versión:** 2.0.0

---

## 📋 Resumen Ejecutivo

Este documento describe la propuesta de integración de **RabbitMQ** en el sistema LogsAnomaly para mejorar la robustez, escalabilidad y manejo de mensajería asíncrona. La integración reemplazará el uso actual de Redis para colas de procesamiento y notificaciones, manteniendo Redis únicamente para cache y estado rápido.

---

## 🎯 Objetivos

### Objetivos Principales
1. **Mejorar robustez** en el procesamiento de mensajes
2. **Desacoplar servicios** mediante mensajería asíncrona
3. **Simplificar comunicación** eliminando webhooks y streaming complejo en Nginx
4. **Mantener simplicidad** para uso interno de equipos

### Beneficios Esperados
- ✅ Manejo robusto de errores con Dead Letter Queues
- ✅ Escalabilidad horizontal sin cambios en código
- ✅ Mejor observabilidad con RabbitMQ Management UI
- ✅ Patrones de mensajería probados y estándar

---

## 🏗️ Arquitectura Propuesta

### Separación de Responsabilidades

#### Redis (Mantener)
**Propósito:** Cache y estado rápido
- Cache de resultados LLM (evitar llamadas repetidas)
- Cache de features extraídas de logs
- Estado rápido de sesiones WebSocket
- Datos temporales con TTL corto

**Razón:** Redis es excelente para cache de alta velocidad y datos temporales.

#### RabbitMQ (Nuevo)
**Propósito:** Mensajería y colas de trabajo
- Colas de procesamiento de chunks
- Mensajería entre servicios backend
- Notificaciones de estado de jobs
- Manejo de errores y reintentos

**Razón:** RabbitMQ ofrece garantías de entrega, acknowledgments, y patrones avanzados de mensajería.

---

## 📊 Estructura de Exchanges y Colas

### Exchange Principal: `anomaly_detection` (Topic)

```
anomaly_detection (Topic Exchange)
│
├── Routing: "chunk.process"
│   └── Queue: chunks_to_process
│       ├── Durable: Sí
│       ├── Prefetch: 1 mensaje por worker
│       ├── TTL: 1 hora por mensaje
│       └── DLQ: chunks_to_process.dlq
│
├── Routing: "chunk.completed"
│   └── Queue: chunks_completed
│       └── Durable: Sí
│
├── Routing: "job.status"
│   └── Exchange: notifications (Fanout)
│       ├── Queue: job_status_updates (WebSocket)
│       └── Queue: job_notifications (otros servicios)
│
└── Routing: "anomaly.detected"
    └── Queue: anomalies_to_explain
        ├── Durable: Sí
        ├── Prioridades: 0-10
        └── Prefetch: 5 (procesamiento batch)
```

### Colas Detalladas

#### 1. `chunks_to_process`
- **Tipo:** Cola de trabajo principal
- **Consumidores:** Workers de procesamiento (4-8 workers)
- **Características:**
  - Durable (sobrevive reinicios)
  - Prefetch count: 1 (un chunk por worker a la vez)
  - TTL por mensaje: 1 hora
  - Dead Letter Exchange: `anomaly_detection`
  - Dead Letter Routing Key: `chunk.failed`

#### 2. `chunks_completed`
- **Tipo:** Cola de resultados
- **Consumidores:** Servicio de actualización de estado
- **Propósito:** Actualizar PostgreSQL con resultados de chunks procesados

#### 3. `notifications` (Fanout Exchange)
- **Tipo:** Broadcast de notificaciones
- **Colas asociadas:**
  - `job_status_updates`: Para WebSocket connections
  - `job_notifications`: Para otros servicios que necesiten escuchar

#### 4. `anomalies_to_explain`
- **Tipo:** Cola de trabajo para LLM
- **Consumidores:** Workers de explicación LLM
- **Características:**
  - Prioridades: 0-10 (10 = más urgente)
  - Prefetch: 5 (procesamiento en batch)
  - Permite procesar múltiples anomalías simultáneamente

#### 5. `chunks_to_process.dlq` (Dead Letter Queue)
- **Tipo:** Cola de mensajes fallidos
- **Propósito:** Capturar mensajes que fallaron después de N reintentos
- **Uso:** Debugging y reprocesamiento manual

---

## 🔄 Flujos de Procesamiento

### Flujo 1: Procesamiento de Chunk

```
1. ChunkService crea chunks → Publica a "chunk.process"
2. RabbitMQ enruta a cola "chunks_to_process"
3. Worker consume mensaje (acknowledgment manual)
4. Worker procesa chunk:
   - Extrae features
   - Detecta anomalías (Isolation Forest)
   - Publica anomalías a "anomaly.detected"
5. Worker publica resultado a "chunk.completed"
6. Servicio de estado consume "chunk.completed"
7. Actualiza PostgreSQL con resultados
8. Publica update a "job.status" → Fanout a todos los listeners
```

### Flujo 2: Explicación de Anomalías

```
1. Worker detecta anomalía → Publica a "anomaly.detected"
2. RabbitMQ enruta a cola "anomalies_to_explain"
3. Worker LLM consume (batch de 5)
4. Worker LLM:
   - Verifica cache en Redis primero
   - Si no está en cache, llama a Ollama Cloud
   - Guarda resultado en cache Redis
5. Publica explicación completa a "chunk.completed"
```

### Flujo 3: Notificaciones en Tiempo Real

```
1. Cualquier servicio publica a "job.status"
2. RabbitMQ Fanout Exchange distribuye a todas las colas
3. Backend consume de "job_status_updates"
4. Backend envía update por WebSocket al frontend
5. Frontend actualiza UI en tiempo real
```

---

## 🛡️ Manejo de Errores

### Estrategia de Reintentos

1. **Primer intento:** Procesamiento normal
2. **Fallo:** Mensaje se rechaza (nack) y vuelve a la cola
3. **Reintentos automáticos:** Hasta 3 intentos con backoff exponencial
4. **Después de 3 fallos:** Mensaje va a Dead Letter Queue

### Dead Letter Queue (DLQ)

**Propósito:**
- Capturar mensajes que fallaron repetidamente
- Permitir análisis y debugging
- Reprocesamiento manual si es necesario

**Monitoreo:**
- Alertar si DLQ tiene mensajes
- Dashboard para revisar mensajes fallidos
- Logs detallados de errores

---

## ⚙️ Configuración de Workers

### Workers de Procesamiento

**Configuración:**
- Cantidad: 4-8 workers (configurable)
- Prefetch: 1 mensaje por worker
- Acknowledgment: Manual (después de procesar exitosamente)
- Timeout: 5 minutos por chunk

**Escalabilidad:**
- Agregar workers dinámicamente según carga
- Balanceo automático por RabbitMQ
- Sin cambios en código necesario

### Workers de Explicación LLM

**Configuración:**
- Cantidad: 2-4 workers (menos crítico)
- Prefetch: 5 mensajes (batch processing)
- Acknowledgment: Manual después de batch completo
- Priorización: Procesar anomalías urgentes primero

---

## 📈 Monitoreo y Observabilidad

### RabbitMQ Management UI

**Acceso:** `http://localhost:15672`

**Métricas disponibles:**
- Mensajes en cola (rate, total)
- Throughput (mensajes/segundo)
- Conexiones activas
- Consumidores por cola
- Mensajes en DLQ

### Integración con Dashboard

**Métricas a exponer:**
- Tiempo promedio de procesamiento por chunk
- Tasa de éxito/fallo
- Mensajes pendientes en colas
- Workers activos
- Mensajes en DLQ (alerta si > 0)

---

## 🔧 Configuración Técnica

### Variables de Entorno

```bash
# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Configuración de Workers
WORKER_PROCESSING_COUNT=4
WORKER_LLM_COUNT=2
WORKER_PREFETCH_PROCESSING=1
WORKER_PREFETCH_LLM=5

# Redis (solo cache ahora)
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=3600
```

### Docker Compose

**Servicio RabbitMQ:**
- Imagen: `rabbitmq:3.12-management-alpine`
- Puertos: 5672 (AMQP), 15672 (Management UI)
- Volumen persistente para datos
- Health check configurado

**Dependencias:**
- `anomaly-detector` depende de `rabbitmq` (service_healthy)

---

## 🚀 Plan de Implementación

### Fase 1: Setup Inicial (Semana 1)
- [ ] Agregar servicio RabbitMQ a docker-compose.yml
- [ ] Crear servicio de mensajería base
- [ ] Configurar exchanges y colas principales
- [ ] Tests básicos de conectividad

### Fase 2: Migración de Colas (Semana 2)
- [ ] Migrar cola de chunks de Redis a RabbitMQ
- [ ] Actualizar workers para consumir de RabbitMQ
- [ ] Mantener Redis como fallback temporal
- [ ] Tests de procesamiento end-to-end

### Fase 3: Notificaciones (Semana 3)
- [ ] Implementar Fanout Exchange para notificaciones
- [ ] Migrar WebSocket updates a RabbitMQ
- [ ] Mantener Redis Pub/Sub como fallback
- [ ] Tests de notificaciones en tiempo real

### Fase 4: Optimización (Semana 4)
- [ ] Implementar Dead Letter Queue
- [ ] Configurar reintentos y backoff
- [ ] Agregar métricas y monitoreo
- [ ] Documentación completa

### Fase 5: Limpieza (Semana 5)
- [ ] Eliminar código de Redis para colas
- [ ] Dejar Redis solo para cache
- [ ] Optimizar configuración
- [ ] Revisión final y testing

---

## 📊 Comparación: Antes vs Después

### Antes (Redis para todo)

| Aspecto | Implementación |
|---------|---------------|
| Colas | Redis Lists (`brpop`) |
| Notificaciones | Redis Pub/Sub |
| Cache | Redis Strings/Hashes |
| Manejo de errores | Manual, sin garantías |
| Escalabilidad | Limitada por Redis |
| Observabilidad | Básica (Redis CLI) |

### Después (RabbitMQ + Redis)

| Aspecto | Implementación |
|---------|---------------|
| Colas | RabbitMQ (con garantías) |
| Notificaciones | RabbitMQ Fanout |
| Cache | Redis (optimizado) |
| Manejo de errores | DLQ automático |
| Escalabilidad | Horizontal fácil |
| Observabilidad | Management UI + métricas |

---

## ⚖️ Trade-offs

### Ventajas

✅ **Robustez:** Garantías de entrega y acknowledgments  
✅ **Escalabilidad:** Agregar workers sin cambios en código  
✅ **Observabilidad:** UI completa de gestión  
✅ **Estándar:** Patrones probados en la industria  
✅ **Manejo de errores:** DLQ y reintentos automáticos  

### Desventajas

⚠️ **Complejidad:** Otro servicio que mantener  
⚠️ **Recursos:** Requiere memoria adicional  
⚠️ **Curva de aprendizaje:** Nuevo concepto para el equipo  
⚠️ **Overhead:** Ligeramente más lento que Redis directo  

### Mitigación

- **Complejidad:** Documentación clara y ejemplos
- **Recursos:** RabbitMQ es ligero (~100MB base)
- **Curva de aprendizaje:** Training básico y ejemplos
- **Overhead:** Negligible para uso interno

---

## 🎯 Casos de Uso Específicos

### Caso 1: Procesamiento de Archivo Grande (2GB)

**Flujo:**
1. Archivo se divide en ~2000 chunks (1MB cada uno)
2. Todos los chunks se publican a `chunks_to_process`
3. 4-8 workers procesan en paralelo
4. Cada chunk completado actualiza progreso
5. Frontend recibe updates en tiempo real vía WebSocket

**Beneficios con RabbitMQ:**
- Balanceo automático entre workers
- Si un worker falla, mensaje vuelve a la cola
- Progreso preciso y confiable

### Caso 2: Anomalía Detectada Requiere Explicación

**Flujo:**
1. Worker detecta anomalía con score alto
2. Publica a `anomalies_to_explain` con prioridad 10
3. Worker LLM consume (batch de 5)
4. Verifica cache Redis primero
5. Si no está, llama Ollama Cloud
6. Guarda en cache y publica resultado

**Beneficios con RabbitMQ:**
- Priorización de anomalías críticas
- Batch processing eficiente
- Desacoplamiento entre detección y explicación

### Caso 3: Múltiples Clientes Escuchando Updates

**Flujo:**
1. Job de procesamiento en curso
2. Múltiples usuarios conectados vía WebSocket
3. Backend publica update a Fanout Exchange
4. Todos los clientes reciben el mismo update
5. Frontend actualiza UI para todos

**Beneficios con RabbitMQ:**
- Un solo publish, múltiples consumidores
- Escalable a muchos clientes
- Sin carga adicional en backend

---

## 🔍 Consideraciones de Diseño

### Decisión 1: Topic vs Direct Exchange

**Elegido:** Topic Exchange  
**Razón:** Permite routing flexible y futuro crecimiento

### Decisión 2: Prefetch Count

**Procesamiento:** Prefetch = 1  
**Razón:** Evita que un worker se sobrecargue con chunks grandes

**LLM:** Prefetch = 5  
**Razón:** Batch processing es más eficiente para llamadas API

### Decisión 3: Acknowledgment Manual vs Automático

**Elegido:** Manual  
**Razón:** Control total sobre cuándo se considera procesado

### Decisión 4: Mantener Redis para Cache

**Elegido:** Sí  
**Razón:** Redis es superior para cache de alta velocidad

---

## 📚 Referencias y Recursos

### Documentación
- [RabbitMQ Best Practices](https://www.rabbitmq.com/best-practices.html)
- [RabbitMQ Patterns](https://www.rabbitmq.com/getstarted.html)
- [Dead Letter Queues](https://www.rabbitmq.com/dlx.html)

### Herramientas
- RabbitMQ Management UI: `http://localhost:15672`
- RabbitMQ CLI Tools: `rabbitmqctl`

---

## ✅ Checklist de Validación

Antes de considerar la implementación completa:

- [ ] RabbitMQ funcionando en desarrollo
- [ ] Workers consumiendo correctamente
- [ ] Notificaciones llegando al frontend
- [ ] DLQ capturando errores correctamente
- [ ] Métricas disponibles en Management UI
- [ ] Performance aceptable (sin degradación)
- [ ] Documentación actualizada
- [ ] Equipo entrenado en RabbitMQ básico

---

## 🎓 Próximos Pasos

1. **Revisar esta propuesta** con el equipo
2. **Validar arquitectura** con casos de uso reales
3. **Decidir timeline** de implementación
4. **Preparar ambiente** de desarrollo
5. **Comenzar Fase 1** del plan de implementación

---

**Última actualización:** 18 de diciembre de 2025  
**Autor:** Discusión técnica equipo LogsAnomaly  
**Estado:** Propuesta lista para revisión

