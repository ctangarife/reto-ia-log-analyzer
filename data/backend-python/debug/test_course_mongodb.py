"""
Test MongoDB Integration for Course Generation
Verifies that the course generation service correctly queries MongoDB for anomalies
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import db_manager
from services.course_generation_service import course_generation_service


async def main():
    """Test MongoDB integration for course generation"""
    print("=" * 80)
    print("TEST: MongoDB Integration para Course Generation")
    print("=" * 80)

    # Connect to databases
    print("\n1. Conectando a bases de datos...")
    await db_manager.connect_mongodb()
    await db_manager.connect_postgres()
    print("✅ Conectado")

    # Test 1: List available projects with completed jobs
    print("\n2. Buscando proyectos con trabajos completados...")
    async with db_manager.postgres_pool.acquire() as conn:
        projects = await conn.fetch("""
            SELECT p.id, p.name, COUNT(j.id) as completed_jobs
            FROM auth.projects p
            LEFT JOIN processing.processing_jobs j ON j.project_id = p.id AND j.status = 'completed'
            GROUP BY p.id, p.name
            HAVING COUNT(j.id) > 0
            LIMIT 5
        """)

    if not projects:
        print("⚠️  No hay proyectos con trabajos completados.")
        print("   Primero debes procesar algunos archivos de logs.")
        await db_manager.mongodb_client.close()
        await db_manager.postgres_pool.close()
        return

    print(f"✅ Encontrados {len(projects)} proyectos:")
    for p in projects:
        print(f"   - {p['name']} (ID: {p['id']}) - {p['completed_jobs']} trabajos completados")

    # Test with first project
    test_project = projects[0]
    project_id = test_project['id']

    # Test 2: Count anomalies in MongoDB
    print(f"\n3. Contando anomalías en MongoDB para el proyecto...")
    async with db_manager.postgres_pool.acquire() as conn:
        total_anomalies = await course_generation_service._count_project_anomalies(conn, project_id)
    print(f"✅ Total de anomalías encontradas: {total_anomalies}")

    if total_anomalies == 0:
        print("⚠️  No hay anomalías en MongoDB.")
        await db_manager.mongodb_client.close()
        await db_manager.postgres_pool.close()
        return

    # Test 3: Get anomalies analysis
    print(f"\n4. Analizando anomalías del proyecto...")
    analysis = await course_generation_service._get_anomalies_analysis(conn, project_id)
    print(f"✅ Análisis completado:")
    print(f"   - Total: {analysis['total']}")
    print(f"   - Categorías: {analysis['categories']}")
    print(f"   - Severidad: {analysis['severity']}")

    # Test 4: Get sample anomalies
    print(f"\n5. Obteniendo muestras de anomalías...")
    samples = await course_generation_service._get_sample_anomalies(project_id, count=3)
    print(f"✅ Muestras obtenidas: {len(samples)}")
    for i, sample in enumerate(samples, 1):
        print(f"\n   Muestra {i}:")
        print(f"   - Tipo: {sample['type']}")
        print(f"   - Score: {sample['score']:.2f}")
        print(f"   - Log: {sample['log_entry'][:60]}...")

    # Test 5: Check if course can be generated
    print(f"\n6. Verificando si se puede generar curso...")
    can_generate = await course_generation_service.can_generate_course(project_id)
    print(f"✅ Puede generar curso: {can_generate['can_generate']}")
    if not can_generate['can_generate']:
        print(f"   Razón: {can_generate.get('reason', 'Unknown')}")
    else:
        print(f"   Anomalías suficientes: {can_generate.get('anomalies_count', 0)}")

    # Test 6: Preview course data
    if can_generate['can_generate']:
        print(f"\n7. Generando vista previa del curso...")
        preview = await course_generation_service.preview_course_data(project_id)
        print(f"✅ Vista previa generada:")
        print(f"   - Proyecto: {preview.project_name}")
        print(f"   - Total logs: {preview.total_logs}")
        print(f"   - Total anomalías: {preview.total_anomalies}")
        print(f"   - Formatos: {preview.log_formats}")
        print(f"   - Puede generar: {preview.can_generate_course}")

    # Cleanup
    print("\n" + "=" * 80)
    print("Cerrando conexiones...")
    await db_manager.mongodb_client.close()
    await db_manager.postgres_pool.close()
    print("✅ Tests completados")


if __name__ == "__main__":
    asyncio.run(main())
