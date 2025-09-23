#!/usr/bin/env python3
"""
Script de prueba para verificar la implementación de endpoints V2
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
TEST_FILE_PATH = "test_logs.txt"

async def test_v2_endpoints():
    """Prueba todos los endpoints V2"""
    print("🚀 Iniciando pruebas de endpoints V2...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Verificar health check
        print("\n1. Verificando health check...")
        try:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check OK: {data}")
                else:
                    print(f"❌ Health check falló: {response.status}")
        except Exception as e:
            print(f"❌ Error en health check: {e}")
        
        # 2. Crear archivo de prueba si no existe
        if not os.path.exists(TEST_FILE_PATH):
            print(f"\n2. Creando archivo de prueba: {TEST_FILE_PATH}")
            test_logs = [
                "192.168.1.1 - - [25/Dec/2023:10:00:01 +0000] \"GET /api/users HTTP/1.1\" 200 1234",
                "192.168.1.2 - - [25/Dec/2023:10:00:02 +0000] \"POST /api/login HTTP/1.1\" 401 567",
                "192.168.1.3 - - [25/Dec/2023:10:00:03 +0000] \"GET /api/data HTTP/1.1\" 200 890",
                "192.168.1.4 - - [25/Dec/2023:10:00:04 +0000] \"DELETE /api/users/123 HTTP/1.1\" 403 234",
                "192.168.1.5 - - [25/Dec/2023:10:00:05 +0000] \"GET /api/health HTTP/1.1\" 200 45"
            ]
            with open(TEST_FILE_PATH, 'w') as f:
                f.write('\n'.join(test_logs))
            print(f"✅ Archivo de prueba creado con {len(test_logs)} logs")
        
        # 3. Probar endpoint de procesamiento V2
        print(f"\n3. Probando endpoint /api/v2/process...")
        try:
            with open(TEST_FILE_PATH, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=TEST_FILE_PATH)
                
                async with session.post(f"{BASE_URL}/api/v2/process", data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        job_id = result.get('job_id')
                        print(f"✅ Procesamiento iniciado: {result}")
                        print(f"📋 Job ID: {job_id}")
                        
                        # 4. Probar endpoint de estado
                        print(f"\n4. Probando endpoint /api/v2/status/{job_id}...")
                        await asyncio.sleep(2)  # Esperar un poco
                        
                        async with session.get(f"{BASE_URL}/api/v2/status/{job_id}") as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                print(f"✅ Estado obtenido: {status_data}")
                            else:
                                print(f"❌ Error obteniendo estado: {status_response.status}")
                        
                        # 5. Probar endpoint de streaming (opcional)
                        print(f"\n5. Probando endpoint de streaming...")
                        try:
                            async with session.get(f"{BASE_URL}/api/v2/results/{job_id}/stream") as stream_response:
                                if stream_response.status == 200:
                                    print("✅ Streaming iniciado")
                                    # Leer algunas líneas del stream
                                    count = 0
                                    async for line in stream_response.content:
                                        if count >= 3:  # Solo leer 3 líneas
                                            break
                                        print(f"📡 Stream data: {line.decode().strip()}")
                                        count += 1
                                else:
                                    print(f"❌ Error en streaming: {stream_response.status}")
                        except Exception as e:
                            print(f"⚠️  Streaming no disponible: {e}")
                        
                        # 6. Probar endpoint de cancelación (opcional)
                        print(f"\n6. Probando endpoint de cancelación...")
                        try:
                            async with session.post(f"{BASE_URL}/api/v2/cancel/{job_id}") as cancel_response:
                                if cancel_response.status == 200:
                                    cancel_data = await cancel_response.json()
                                    print(f"✅ Cancelación exitosa: {cancel_data}")
                                else:
                                    print(f"❌ Error cancelando: {cancel_response.status}")
                        except Exception as e:
                            print(f"⚠️  Cancelación no disponible: {e}")
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Error en procesamiento: {response.status} - {error_text}")
                        
        except Exception as e:
            print(f"❌ Error probando procesamiento: {e}")
    
    print("\n🎉 Pruebas completadas!")

async def test_database_connections():
    """Prueba las conexiones a las bases de datos"""
    print("\n🔍 Verificando conexiones a bases de datos...")
    
    # Verificar MongoDB
    try:
        import motor.motor_asyncio
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://admin:password@localhost:27017/logsanomaly")
        await client.admin.command('ping')
        print("✅ MongoDB: Conexión exitosa")
        client.close()
    except Exception as e:
        print(f"❌ MongoDB: Error de conexión - {e}")
    
    # Verificar PostgreSQL
    try:
        import asyncpg
        conn = await asyncpg.connect("postgresql://anomaly_user:anomaly_password@localhost:5432/logsanomaly")
        await conn.execute("SELECT 1")
        await conn.close()
        print("✅ PostgreSQL: Conexión exitosa")
    except Exception as e:
        print(f"❌ PostgreSQL: Error de conexión - {e}")
    
    # Verificar Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url("redis://localhost:6379/0")
        await r.ping()
        await r.close()
        print("✅ Redis: Conexión exitosa")
    except Exception as e:
        print(f"❌ Redis: Error de conexión - {e}")

if __name__ == "__main__":
    print("🧪 Script de prueba para implementación V2")
    print("=" * 50)
    
    # Ejecutar pruebas
    asyncio.run(test_database_connections())
    asyncio.run(test_v2_endpoints())
