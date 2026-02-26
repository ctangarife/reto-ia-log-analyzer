import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from main import app, extract_features, detect_anomalies

client = TestClient(app)

def test_health_check():
    """Prueba el endpoint de health check"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_extract_features():
    """Prueba la extracción de características"""
    log_text = "2024-01-01 10:00:00 ERROR Failed to connect to database"
    features = extract_features(log_text)
    
    assert len(features) == 7  # Número esperado de características
    assert features[0] > 0  # Longitud del texto
    assert features[1] > 0  # Número de palabras
    assert features[2] > 0  # Entropía
    assert features[3] >= 0  # Palabras clave sospechosas
    assert features[4] >= 0  # Caracteres especiales
    assert features[5] >= 0  # Números
    assert features[6] > 0   # Longitud promedio de palabras

def test_detect_anomalies():
    """Prueba la detección de anomalías"""
    # Logs normales
    normal_logs = [
        "2024-01-01 10:00:00 INFO User login successful",
        "2024-01-01 10:01:00 INFO Database connection established",
        "2024-01-01 10:02:00 INFO User logout successful",
        "2024-01-01 10:03:00 INFO Backup process completed"
    ]
    
    # Logs anómalos
    anomalous_logs = [
        "2024-01-01 10:04:00 CRITICAL System memory usage exceeded 95%",
        "2024-01-01 10:05:00 FATAL Database corruption detected"
    ]
    
    all_logs = normal_logs + anomalous_logs
    labels, scores = detect_anomalies(all_logs)
    
    assert len(labels) == len(all_logs)
    assert len(scores) == len(all_logs)
    
    # Debería detectar al menos una anomalía
    assert -1 in labels

def test_detect_endpoint_with_file():
    """Prueba el endpoint de detección con archivo"""
    # Crear archivo temporal con logs de prueba
    test_logs = """2024-01-01 10:00:00 INFO User login successful
2024-01-01 10:01:00 INFO Database connection established
2024-01-01 10:02:00 ERROR Failed to connect to external API
2024-01-01 10:03:00 INFO User logout successful
2024-01-01 10:04:00 CRITICAL System memory usage exceeded 95%"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_logs)
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            response = client.post(
                "/detect",
                files={"file": ("test_logs.txt", f, "text/plain")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_logs" in data
        assert "anomalies_detected" in data
        assert "anomalies" in data
        assert "report_file" in data
        
        assert data["total_logs"] == 5
        assert data["anomalies_detected"] >= 0
        
    finally:
        os.unlink(temp_file)

def test_detect_endpoint_with_json():
    """Prueba el endpoint de detección con JSON"""
    test_logs = [
        {"content": "2024-01-01 10:00:00 INFO User login successful"},
        {"content": "2024-01-01 10:01:00 INFO Database connection established"},
        {"content": "2024-01-01 10:02:00 ERROR Failed to connect to external API"},
        {"content": "2024-01-01 10:03:00 INFO User logout successful"},
        {"content": "2024-01-01 10:04:00 CRITICAL System memory usage exceeded 95%"}
    ]
    
    response = client.post("/detect-text", json=test_logs)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_logs" in data
    assert "anomalies_detected" in data
    assert "anomalies" in data
    assert "report_file" in data
    
    assert data["total_logs"] == 5
    assert data["anomalies_detected"] >= 0

def test_empty_file():
    """Prueba con archivo vacío"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("")
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            response = client.post(
                "/detect",
                files={"file": ("empty.txt", f, "text/plain")}
            )
        
        assert response.status_code == 400
        
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    pytest.main([__file__])
