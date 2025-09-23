#!/usr/bin/env python3
"""
Script simple para probar endpoints V2
"""

import requests
import json

def test_v2_endpoints():
    """Probar endpoints V2"""
    base_url = "http://localhost:8000"
    
    print("🧪 Probando endpoints V2...")
    
    # 1. Verificar health check
    print("\n1. Verificando health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print(f"✅ Health check OK: {response.json()}")
        else:
            print(f"❌ Health check falló: {response.status_code}")
    except Exception as e:
        print(f"❌ Error en health check: {e}")
    
    # 2. Probar endpoint V2 con archivo de prueba
    print("\n2. Probando endpoint /api/v2/process...")
    try:
        with open("data/anomaly-detector/test_logs.txt", "rb") as f:
            files = {"file": f}
            response = requests.post(f"{base_url}/api/v2/process", files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Procesamiento V2 iniciado: {result}")
                job_id = result.get("job_id")
                
                if job_id:
                    # 3. Probar endpoint de estado
                    print(f"\n3. Probando endpoint /api/v2/status/{job_id}...")
                    try:
                        status_response = requests.get(f"{base_url}/api/v2/status/{job_id}")
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"✅ Estado obtenido: {status_data}")
                        else:
                            print(f"❌ Error obteniendo estado: {status_response.status_code}")
                            print(f"Respuesta: {status_response.text}")
                    except Exception as e:
                        print(f"❌ Error probando estado: {e}")
            else:
                print(f"❌ Error en procesamiento V2: {response.status_code}")
                print(f"Respuesta: {response.text}")
                
    except Exception as e:
        print(f"❌ Error probando procesamiento V2: {e}")
    
    print("\n🎉 Pruebas completadas!")

if __name__ == "__main__":
    test_v2_endpoints()
