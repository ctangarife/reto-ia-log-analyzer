import random
import datetime
import json as json_module  # Renombrado para evitar conflicto
import os

def generate_test_logs(size_mb: int, anomaly_ratio: float = 0.1, pattern: str = "normal") -> tuple:
    """
    Genera logs de prueba con diferentes patrones
    
    Args:
        size_mb: Tamaño aproximado del archivo en MB
        anomaly_ratio: Ratio de anomalías (0.0 - 1.0)
        pattern: "normal", "high_volume", "high_anomaly"
    
    Returns:
        tuple: (path_to_txt, path_to_json)
    """
    
    # Templates de logs
    normal_templates = [
        "INFO [{}] User {} logged in successfully from IP {}",
        "DEBUG [{}] Request processed in {}ms for endpoint {}",
        "INFO [{}] Database query completed in {}ms",
        "INFO [{}] Cache hit ratio: {}%",
        "DEBUG [{}] Memory usage at {}%"
    ]
    
    error_templates = [
        "ERROR [{}] Failed login attempt for user {} from IP {} - Invalid credentials",
        "ERROR [{}] Database connection timeout after {}ms",
        "CRITICAL [{}] Memory usage critical at {}%",
        "ERROR [{}] Rate limit exceeded for IP {}",
        "WARN [{}] Suspicious activity detected from IP {}"
    ]
    
    # Datos para generar logs realistas
    usernames = ["john.doe", "alice.smith", "bob.jones", "admin", "system"]
    ips = [f"192.168.1.{i}" for i in range(1, 255)]
    endpoints = ["/api/users", "/api/auth", "/api/data", "/api/metrics", "/api/logs"]
    
    # Ajustar parámetros según el patrón
    if pattern == "high_volume":
        normal_templates *= 3  # Más variedad de logs normales
        anomaly_ratio *= 0.5  # Menos anomalías
    elif pattern == "high_anomaly":
        error_templates *= 2   # Más variedad de errores
        anomaly_ratio *= 2    # Más anomalías
    
    # Calcular número aproximado de líneas para alcanzar el tamaño deseado
    avg_line_size = 100  # tamaño promedio en bytes
    target_lines = (size_mb * 1024 * 1024) // avg_line_size
    
    logs = []
    json_logs = []
    
    for i in range(target_lines):
        timestamp = datetime.datetime.now() - datetime.timedelta(
            seconds=random.randint(0, 86400)  # Últimas 24 horas
        )
        
        # Decidir si esta línea será una anomalía
        is_anomaly = random.random() < anomaly_ratio
        
        if is_anomaly:
            template = random.choice(error_templates)
            log_data = {
                "timestamp": timestamp.isoformat(),
                "level": "ERROR",
                "user": random.choice(usernames),
                "ip": random.choice(ips),
                "latency": random.randint(1000, 5000),
                "memory": random.randint(85, 100),
                "is_anomaly": True
            }
        else:
            template = random.choice(normal_templates)
            log_data = {
                "timestamp": timestamp.isoformat(),
                "level": "INFO",
                "user": random.choice(usernames),
                "ip": random.choice(ips),
                "latency": random.randint(10, 200),
                "memory": random.randint(20, 80),
                "is_anomaly": False
            }
        
        # Generar log en formato texto
        log_line = template.format(
            timestamp.isoformat(),
            log_data["user"],
            log_data["ip"],
            log_data.get("latency", ""),
            log_data.get("memory", "")
        )
        
        logs.append(log_line)
        json_logs.append(log_data)
    
    # Crear directorio si no existe
    os.makedirs("test_data", exist_ok=True)
    
    # Guardar archivos
    base_name = f"logs_{pattern}_{size_mb}mb"
    txt_path = f"test_data/{base_name}.txt"
    json_path = f"test_data/{base_name}.json"
    
    # Guardar archivo de texto
    with open(txt_path, "w") as f:
        f.write("\n".join(logs))
    
    # Guardar archivo JSON
    with open(json_path, "w") as f:
        json_module.dump(json_logs, f, indent=2)
    
    return txt_path, json_path

if __name__ == "__main__":
    # Generar diferentes sets de prueba
    test_sets = [
        (1, 0.1, "normal"),      # 1MB, 10% anomalías, patrón normal
        (10, 0.1, "normal"),     # 10MB, 10% anomalías, patrón normal
        (50, 0.05, "normal"),    # 50MB, 5% anomalías, patrón normal
        (10, 0.2, "high_anomaly"), # 10MB, 20% anomalías
        (10, 0.1, "high_volume"),  # 10MB, alta variedad de logs normales
    ]
    
    for size, ratio, pattern in test_sets:
        print(f"Generando logs {pattern} de {size}MB...")
        txt, json_file = generate_test_logs(size, ratio, pattern)
        print(f"Archivos generados: {txt}, {json_file}")