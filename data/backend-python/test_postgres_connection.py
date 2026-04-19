#!/usr/bin/env python3
"""Script temporal para probar conexión a PostgreSQL"""
import os
import asyncio
import asyncpg

async def test_connection():
    postgres_user = os.getenv("POSTGRES_USER", "anomaly_user")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "anomaly_password")
    postgres_db = os.getenv("POSTGRES_DB", "logsanomaly")
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
    
    print(f"Testing connection:")
    print(f"  Host: {postgres_host}")
    print(f"  Port: {postgres_port}")
    print(f"  User: {postgres_user}")
    print(f"  Database: {postgres_db}")
    print(f"  Password length: {len(postgres_password)}")
    print(f"  Password value: [{postgres_password}]")
    print(f"  Password repr: {repr(postgres_password)}")
    
    try:
        conn = await asyncpg.connect(
            host=postgres_host,
            port=postgres_port,
            user=postgres_user,
            password=postgres_password,
            database=postgres_db
        )
        print("✅ Connection successful!")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
