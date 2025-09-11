import random
import datetime
import json
import os

def generate_normal_log():
    """Genera un log normal"""
    actions = [
        "User login successful",
        "Database connection established",
        "File uploaded successfully",
        "Cache updated",
        "Session created",
        "Request processed",
        "Data synchronized",
        "Backup completed",
        "Service health check passed",
        "Configuration loaded"
    ]
    return random.choice(actions)

def generate_anomaly_log():
    """Genera un log anómalo"""
    anomalies = [
        "CRITICAL: System memory usage at 98%",
        "ERROR: Database connection failed after 5 retries",
        "ALERT: Unauthorized access attempt from IP 192.168.1.100",
        "FATAL: Disk space critically low (99% used)",
        "ERROR: Unexpected system shutdown",
        "WARNING: Unusual CPU spike detected (95% usage)",
        "CRITICAL: Multiple failed login attempts detected",
        "ERROR: Data corruption detected in primary storage",
        "ALERT: Possible SQL injection attempt detected",
        "FATAL: Main process crashed unexpectedly"
    ]
    return random.choice(anomalies)

def generate_timestamp(start_date=None):
    """Genera un timestamp dentro de un rango"""
    if not start_date:
        start_date = datetime.datetime.now() - datetime.timedelta(days=1)
    
    time_offset = datetime.timedelta(
        seconds=random.randint(0, 24*60*60)
    )
    return (start_date + time_offset).strftime("%Y-%m-%d %H:%M:%S")

def generate_log_file(filename, num_logs=100, anomaly_ratio=0.1):
    """Genera un archivo de logs con una proporción de anomalías"""
    logs = []
    num_anomalies = int(num_logs * anomaly_ratio)
    
    # Generar logs normales
    for _ in range(num_logs - num_anomalies):
        log = {
            "timestamp": generate_timestamp(),
            "content": generate_normal_log(),
            "level": "INFO"
        }
        logs.append(log)
    
    # Generar logs anómalos
    for _ in range(num_anomalies):
        log = {
            "timestamp": generate_timestamp(),
            "content": generate_anomaly_log(),
            "level": "ERROR"
        }
        logs.append(log)
    
    # Mezclar los logs y ordenar por timestamp
    random.shuffle(logs)
    logs.sort(key=lambda x: x["timestamp"])
    
    # Guardar en formato JSON y texto plano
    with open(f"{filename}.json", "w") as f:
        json.dump(logs, f, indent=2)
    
    with open(f"{filename}.txt", "w") as f:
        for log in logs:
            f.write(f"{log['timestamp']} {log['level']}: {log['content']}\n")

if __name__ == "__main__":
    # Crear directorio de test_data si no existe
    os.makedirs("test_data", exist_ok=True)
    
    # Generar diferentes conjuntos de logs
    scenarios = [
        ("normal", 100, 0.05),  # 5% anomalías
        ("high_anomaly", 100, 0.20),  # 20% anomalías
        ("low_volume", 20, 0.10),  # Pocos logs
        ("high_volume", 1000, 0.10),  # Muchos logs
    ]
    
    for name, num_logs, ratio in scenarios:
        print(f"Generando {name} con {num_logs} logs ({ratio*100}% anomalías)...")
        generate_log_file(f"test_data/logs_{name}", num_logs, ratio)
    
    print("\nArchivos generados en el directorio test_data/:")
    for name, _, _ in scenarios:
        print(f"- logs_{name}.json")
        print(f"- logs_{name}.txt")
