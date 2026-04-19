# Configuración de Nginx - Reverse Proxy

Esta carpeta contiene la configuración de Nginx que actúa como **Reverse Proxy** y **Gateway** principal para el sistema Logs Anomaly Detector.

## 📋 Estructura

```
server/nginx/
├── nginx.conf                          # Configuración principal de Nginx
├── conf.d/
│   └── default.conf                    # Configuración del reverse proxy
├── includes/
│   └── security-headers.conf          # Headers de seguridad HTTP
└── README.md                           # Este archivo
```

## 🔒 Seguridad Implementada

### 1. **Acceso Protegido a Backends**
- El servicio backend Python **NO es accesible directamente** desde el exterior
- Solo Nginx puede comunicarse con él a través de la red interna de Docker
- El puerto del backend no se expone públicamente en docker-compose

### 2. **Rate Limiting**
- **APIs generales:** 30 req/s con burst de 10
- **Peticiones generales:** 10 req/s con burst de 20

### 3. **Headers de Seguridad**
- `X-Frame-Options: SAMEORIGIN` - Previene clickjacking
- `X-Content-Type-Options: nosniff` - Previene MIME sniffing
- `X-XSS-Protection` - Protección XSS en navegadores
- `Referrer-Policy` - Control de información de referrer
- `Permissions-Policy` - Control de características del navegador

### 4. **Protección de Archivos Sensibles**
- Bloqueo de archivos `.env`, `.yml`, `.config`
- Bloqueo de archivos ocultos (`.git`, `.htaccess`)
- Denegación de acceso a directorios privados

## 🌐 Enrutamiento

### Frontend (Vue 3)
| Ruta | Destino | Descripción |
|------|---------|-------------|
| `/` | Archivos estáticos | Aplicación web principal (SPA) |
| `*.js, *.css, *.png, etc.` | Archivos estáticos | Assets con cache agresivo (1 año) |

### Backend Python (FastAPI)
| Ruta | Destino | Descripción | Timeout |
|------|---------|-------------|---------|
| `/api/*` | `anomaly-detector:8000` | Todas las APIs del detector | 600s |
| `/api/health` | `anomaly-detector:8000` | Health check | 30s |

## ⚙️ Características Técnicas

### Optimizaciones de Rendimiento
- **Gzip:** Compresión activada para texto, JSON, JS, CSS
- **Keep-Alive:** Conexiones persistentes habilitadas
- **Upstream Keep-Alive:** 32 conexiones mantenidas por upstream
- **Sendfile:** Activado para transferencia eficiente de archivos
- **TCP optimizations:** `tcp_nopush` y `tcp_nodelay` activados
- **Streaming:** Buffering deshabilitado para respuestas en tiempo real

### Timeouts Configurados
| Tipo de Petición | Timeout |
|------------------|---------|
| General | 120s |
| Procesamiento de logs | 600s (10 min) |
| Streaming | Sin límite (chunked transfer) |

### Límites de Tamaño
- **Archivos generales:** 100 MB
- **Carga de logs:** 100 MB
- **Buffers:** 128 KB (cliente), buffers deshabilitados para streaming

## 🏥 Health Checks

### Health Check Público
```bash
curl http://localhost/health
```

### Health Check Interno (solo red Docker)
```bash
curl http://localhost:8080/nginx-health
```

### Métricas de Nginx (solo red interna)
```bash
curl http://localhost:8080/stub_status
```

## 📝 Logs

### Ubicación de Logs
- **Access Log:** `/var/log/nginx/logsanomaly.access.log`
- **Error Log:** `/var/log/nginx/logsanomaly.error.log`

### Formato de Logs
Los logs incluyen formato `detailed` con:
- IP del cliente
- Timestamp
- Petición HTTP
- Status code
- Tiempos de respuesta (request_time, upstream_time)
- User agent
- Referrer

### Ver Logs en Tiempo Real
```bash
# Logs de acceso
docker exec logs-analyze-nginx tail -f /var/log/nginx/logsanomaly.access.log

# Logs de error
docker exec logs-analyze-nginx tail -f /var/log/nginx/logsanomaly.error.log
```

## 🚀 Uso

### En docker-compose.yml
```yaml
services:
  logs-analyze-nginx:
    image: nginx:stable-alpine
    ports:
      - "80:80"        # Puerto público
      - "8080:8080"    # Puerto de health check (no exponer en producción)
    volumes:
      # Montar configuraciones desde el host
      - ./server/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./server/nginx/conf.d:/etc/nginx/conf.d:ro
      - ./server/nginx/includes:/etc/nginx/includes:ro
      - ./data/logs/nginx:/var/log/nginx
      - ./data/static:/usr/share/nginx/html:ro
    depends_on:
      - logs-analyze-ui
      - anomaly-detector
    networks:
      - logs_analyze_net
```

**Nota:** Se usa la imagen oficial de nginx sin necesidad de crear un Dockerfile personalizado.
Los archivos de configuración se montan como volúmenes.

### Verificar Configuración
```bash
# Test de configuración
docker exec logs-analyze-nginx nginx -t

# Recargar configuración sin downtime
docker exec logs-analyze-nginx nginx -s reload
```

## 🛡️ Mejores Prácticas Aplicadas

1. **Separación de Concerns:** Cada servicio maneja su responsabilidad específica
2. **Defense in Depth:** Múltiples capas de seguridad (rate limiting, headers, validación)
3. **Least Privilege:** Backend no expuesto directamente
4. **Logging:** Registro detallado de todas las peticiones
5. **Health Checks:** Monitoreo automático de disponibilidad
6. **Performance:** Optimizaciones de cache, compresión y conexiones
7. **Streaming:** Soporte para respuestas en tiempo real sin buffering

## 📚 Referencias

- [Nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Security Headers](https://securityheaders.com/)
- [Rate Limiting](https://www.nginx.com/blog/rate-limiting-nginx/)
- [Nginx Performance](https://www.nginx.com/blog/tuning-nginx/)
- [Nginx Streaming](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering)

