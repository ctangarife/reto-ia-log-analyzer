# 🚀 Instalación Rápida - Detector de Anomalías en Logs

## ⚡ Instalación Express (5 minutos)

### Paso 1: Prerequisitos
```bash
# Verificar Docker
docker --version
docker-compose --version

# Si no tienes Docker, instálalo desde: https://docs.docker.com/get-docker/
```

### Paso 2: Clonar y Ejecutar
```bash
# Clonar repositorio
git clone https://github.com/ctangarife/reto-ia-log-analyzer.git
cd reto-ia-log-analyzer

# Iniciar todos los servicios
docker-compose up -d
```

### Paso 3: Acceder
- **Interfaz Web**: http://localhost:80
- **API Backend**: http://localhost:8000
- **Ollama API**: http://localhost:11434

### Paso 4: Probar
1. Arrastra un archivo de logs a la interfaz web
2. Haz clic en "Analizar"
3. Espera los resultados en tiempo real

## 🔧 Configuración Rápida por Tipo de Sistema

### 💻 Sistema con poca RAM (< 16GB)
```bash
# Editar docker-compose.yml antes del paso 2
# Cambiar estas líneas:
environment:
  - MODEL_NAME=phi3:mini  # Modelo ligero
# Comentar sección de GPU
```

### 🎮 Sistema con GPU NVIDIA
```bash
# Instalar NVIDIA Container Toolkit primero
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# Verificar GPU disponible
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### 🖥️ Solo CPU (sin GPU)
```bash
# Editar docker-compose.yml:
environment:
  - OLLAMA_DEVICE=cpu
  - MODEL_NAME=phi3:mini
# Comentar toda la sección deploy/resources/devices
```

## ❗ Problemas Comunes

### "No se puede conectar a Docker"
- Asegúrate de que Docker Desktop esté ejecutándose
- En Linux: `sudo systemctl start docker`

### "Out of memory"
- Usa modelo más pequeño: `MODEL_NAME=phi3:mini`
- Cierra otras aplicaciones pesadas

### "Puerto ocupado"
- Cambia puertos en docker-compose.yml si están ocupados
- Por ejemplo: `"8080:80"` en lugar de `"80:80"`

### Descarga lenta del modelo
- Primera vez puede tomar 10-30 minutos
- Verifica conexión a internet
- Usa modelo más pequeño temporalmente

## 🎯 Primeros Pasos

1. **Subir archivo de prueba**: Cualquier archivo .log o .txt
2. **Configurar análisis**: Usa configuración por defecto inicialmente  
3. **Ver resultados**: Las anomalías aparecerán en rojo con explicaciones
4. **Explorar historial**: Los análisis se guardan automáticamente

## 📞 ¿Necesitas ayuda?

- **Documentación completa**: [README.md](./README.md)
- **Configuración de modelos**: [CONFIGURACION-MODELOS.md](./CONFIGURACION-MODELOS.md)
- **Issues**: https://github.com/ctangarife/reto-ia-log-analyzer/issues

---
⭐ Si te gusta el proyecto, ¡dale una estrella en GitHub!