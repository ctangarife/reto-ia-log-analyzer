import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any
import websockets
import os

async def monitor_processing(job_id: str, ws_url: str):
    """Monitorea el progreso del procesamiento vía WebSocket"""
    print(f"Intentando conectar a: {ws_url}")
    async with websockets.connect(ws_url) as websocket:
        print(f"Conectado al WebSocket para job {job_id}")
        
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "batch_progress":
                    print(f"Progreso chunk {data['chunk_number']}: {data['progress']:.2f}%")
                    print(f"Anomalías en batch: {len(data['anomalies'])}")
                    if data['anomalies']:
                        print("Ejemplo de anomalía:")
                        print(f"  Log: {data['anomalies'][0]['log_entry']}")
                        print(f"  Score: {data['anomalies'][0]['score']}")
                        print(f"  Explicación: {data['anomalies'][0]['explanation']}")
                
                elif data["type"] == "job_completed":
                    print("\nProcesamiento completado!")
                    print(f"Total anomalías: {data['total_anomalies']}")
                    print(f"Tiempo total: {data['processing_time']:.2f} segundos")
                    break
                
            except websockets.exceptions.ConnectionClosed:
                print("Conexión WebSocket cerrada")
                break
            except Exception as e:
                print(f"Error en WebSocket: {str(e)}")
                break

async def run_test(file_path: str, api_url: str, ws_url: str):
    """Ejecuta una prueba completa de procesamiento"""
    
    print(f"\nIniciando prueba con archivo: {file_path}")
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    print(f"Tamaño del archivo: {file_size:.2f} MB")
    
    # 1. Iniciar procesamiento
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Subir archivo
            print("Subiendo archivo...")
            with open(file_path, 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('file', f)
                
                async with session.post(f"{api_url}/detect", data=form) as response:
                    if response.status != 200:
                        print(f"Error al subir archivo: {await response.text()}")
                        return
                    
                    result = await response.json()
                    job_id = result["job_id"]
                    print(f"Job ID: {job_id}")
            
            # Monitorear progreso
            print("Monitoreando progreso...")
            await monitor_processing(job_id, f"{ws_url}/ws/jobs/{job_id}")
        
        # Calcular estadísticas
        total_time = time.time() - start_time
        processing_rate = file_size / total_time
        
        print("\nEstadísticas de procesamiento:")
        print(f"Tiempo total: {total_time:.2f} segundos")
        print(f"Tasa de procesamiento: {processing_rate:.2f} MB/s")
        
    except Exception as e:
        print(f"Error durante la prueba: {str(e)}")

async def main():
    """Ejecuta pruebas con diferentes sets de datos"""
    
    # Usar el alias de red de Docker en lugar de localhost
    API_URL = "http://anomaly-detector:8000"
    WS_URL = "ws://anomaly-detector:8000"
    
    # Solo probar con el archivo más pequeño primero
    test_files = [
        "test_data/logs_normal_1mb.txt"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\nProbando con archivo: {test_file}")
            await run_test(test_file, API_URL, WS_URL)
        else:
            print(f"Archivo no encontrado: {test_file}")

if __name__ == "__main__":
    # Primero generar datos de prueba si no existen
    if not os.path.exists("test_data/logs_normal_1mb.txt"):
        print("Generando archivo de prueba de 1MB...")
        import generate_test_logs
        generate_test_logs.generate_test_logs(1, 0.1, "normal")
    
    # Luego ejecutar pruebas
    print("Iniciando pruebas...")
    asyncio.run(main())