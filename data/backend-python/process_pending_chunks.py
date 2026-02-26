#!/usr/bin/env python3
import asyncio
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data', 'anomaly-detector'))

async def process_pending_chunks():
    """Procesar todos los chunks pendientes"""
    print("🔄 Procesando chunks pendientes...")
    
    try:
        # Importar módulos
        from config.database import db_manager
        from services.worker_service import worker_service
        
        # Conectar a bases de datos
        await db_manager.connect_all()
        print("✅ Bases de datos conectadas")
        
        # Obtener todos los chunks pendientes
        pending_chunks = await db_manager.mongodb_client.logsanomaly.chunks.find({
            "processed": False
        }).to_list(length=None)
        
        print(f"📊 Chunks pendientes encontrados: {len(pending_chunks)}")
        
        if not pending_chunks:
            print("✅ No hay chunks pendientes para procesar")
            return
        
        # Agrupar chunks por file_id
        chunks_by_file = {}
        for chunk in pending_chunks:
            file_id = chunk["file_id"]
            if file_id not in chunks_by_file:
                chunks_by_file[file_id] = []
            chunks_by_file[file_id].append(chunk)
        
        print(f"📁 Archivos con chunks pendientes: {len(chunks_by_file)}")
        
        # Procesar cada archivo
        total_processed = 0
        for file_id, chunks in chunks_by_file.items():
            print(f"\n🔧 Procesando archivo {file_id} ({len(chunks)} chunks)...")
            
            # Procesar chunks en paralelo
            results = await worker_service.process_file_async(file_id)
            
            # Contar resultados exitosos
            successful = sum(1 for r in results if not isinstance(r, Exception))
            total_processed += successful
            
            print(f"✅ Archivo {file_id}: {successful}/{len(chunks)} chunks procesados")
            
            # Mostrar errores si los hay
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Error en chunk {i}: {result}")
        
        print(f"\n🎉 Procesamiento completado: {total_processed} chunks procesados")
        
        # Verificar chunks pendientes restantes
        remaining = await db_manager.mongodb_client.logsanomaly.chunks.count_documents({
            "processed": False
        })
        print(f"📊 Chunks pendientes restantes: {remaining}")
        
    except Exception as e:
        print(f"❌ Error procesando chunks: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(process_pending_chunks())
