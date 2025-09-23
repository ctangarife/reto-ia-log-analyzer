#!/usr/bin/env python3
import asyncio
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data', 'anomaly-detector'))

async def debug_workers():
    """Debug directo del sistema de workers"""
    print("🔍 Debug del sistema de workers...")
    
    try:
        # Importar módulos
        from config.database import db_manager
        from services.chunk_service import chunk_service
        from services.worker_service import worker_service
        
        print("✅ Módulos importados correctamente")
        
        # Conectar a bases de datos
        await db_manager.connect_all()
        print("✅ Bases de datos conectadas")
        
        # Verificar chunks pendientes
        chunks_count = await db_manager.mongodb_client.logsanomaly.chunks.count_documents({"processed": False})
        print(f"📊 Chunks pendientes: {chunks_count}")
        
        if chunks_count > 0:
            # Obtener un chunk para procesar
            chunks = await db_manager.mongodb_client.logsanomaly.chunks.find({"processed": False}).limit(1).to_list(length=1)
            
            if chunks:
                chunk = chunks[0]
                print(f"🔧 Procesando chunk: {chunk['_id']}")
                print(f"📄 Tamaño del chunk: {len(chunk['data'])} caracteres")
                print(f"📁 File ID: {chunk['file_id']}")
                
                # Procesar el chunk directamente
                result = await worker_service.process_chunk(chunk)
                print(f"✅ Chunk procesado: {len(result.anomalies)} anomalías encontradas")
                
                # Verificar que se marcó como procesado
                updated_chunk = await db_manager.mongodb_client.logsanomaly.chunks.find_one({"_id": chunk["_id"]})
                print(f"📊 Chunk marcado como procesado: {updated_chunk['processed']}")
                
                # Verificar resultados en MongoDB
                results_count = await db_manager.mongodb_client.logsanomaly.results.count_documents({"chunk_id": str(chunk["_id"])})
                print(f"📈 Resultados guardados: {results_count}")
                
        else:
            print("❌ No hay chunks pendientes para procesar")
            
            # Crear un chunk de prueba
            print("🧪 Creando chunk de prueba...")
            test_content = "2024-01-01 10:00:00 INFO Test log entry\n2024-01-01 10:01:00 ERROR Test error log\n2024-01-01 10:02:00 INFO Another test log"
            file_id = await chunk_service.create_chunks_from_file(test_content, "test_debug.txt")
            print(f"✅ Chunk de prueba creado con file_id: {file_id}")
            
            # Procesar el chunk de prueba
            chunks = await chunk_service.get_chunks_to_process(file_id)
            if chunks:
                print(f"🔧 Procesando {len(chunks)} chunks de prueba...")
                results = await worker_service.process_file_async(file_id)
                print(f"✅ Procesamiento completado: {len(results)} resultados")
                
                # Verificar resultados
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        print(f"❌ Error en chunk {i}: {result}")
                    else:
                        print(f"✅ Chunk {i}: {len(result.anomalies)} anomalías")
        
    except Exception as e:
        print(f"❌ Error en debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_workers())
