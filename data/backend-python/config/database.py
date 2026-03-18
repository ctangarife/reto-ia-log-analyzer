import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import redis.asyncio as redis
from typing import Optional

class DatabaseManager:
    def __init__(self):
        self.mongodb_client: Optional[AsyncIOMotorClient] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None

    @property
    def mongodb_db(self):
        """Get the MongoDB database instance"""
        if self.mongodb_client is None:
            raise RuntimeError("MongoDB client is not connected. Call connect_mongodb() first.")
        mongodb_name = os.getenv("MONGODB_DB", "logsanomaly")
        return self.mongodb_client[mongodb_name]
    
    async def connect_mongodb(self):
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://admin:password@mongodb:27017/logsanomaly?authSource=admin")
        print(f"🔗 Conectando a MongoDB con URI: {mongodb_uri}")
        self.mongodb_client = AsyncIOMotorClient(mongodb_uri, uuidRepresentation='standard')
        await self.mongodb_client.admin.command('ping')
        print("✅ MongoDB conectado")
    
    async def connect_postgres(self):
        # Obtener variables de entorno
        postgres_user = os.getenv("POSTGRES_USER", "anomaly_user")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "anomaly_password")
        postgres_db = os.getenv("POSTGRES_DB", "logsanomaly")
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        
        # Debug: verificar qué contraseña se está usando (solo mostrar primeros y últimos caracteres)
        password_preview = f"{postgres_password[:2]}...{postgres_password[-2:]}" if len(postgres_password) > 4 else "***"
        print(f"🔗 Conectando a PostgreSQL: {postgres_user}@{postgres_host}:{postgres_port}/{postgres_db}")
        print(f"🔍 Debug - Password length: {len(postgres_password)}, Preview: {password_preview}")
        
        # Usar parámetros directamente en lugar de DSN string para evitar problemas con caracteres especiales
        self.postgres_pool = await asyncpg.create_pool(
            host=postgres_host,
            port=postgres_port,
            user=postgres_user,
            password=postgres_password,
            database=postgres_db,
            server_settings={
                'search_path': 'auth,processing,learning,public'
            }
        )
        print("✅ PostgreSQL conectado (schemas: auth, processing, learning, public)")
    
    async def connect_redis(self):
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis_client = redis.from_url(redis_url)
        await self.redis_client.ping()
        print("✅ Redis conectado")
    
    async def connect_all(self):
        await self.connect_mongodb()
        await self.connect_postgres()
        await self.connect_redis()

# Instancia global
db_manager = DatabaseManager()
