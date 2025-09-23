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
    
    async def connect_mongodb(self):
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://admin:password@mongodb:27017/logsanomaly?authSource=admin")
        print(f"🔗 Conectando a MongoDB con URI: {mongodb_uri}")
        self.mongodb_client = AsyncIOMotorClient(mongodb_uri, uuidRepresentation='standard')
        await self.mongodb_client.admin.command('ping')
        print("✅ MongoDB conectado")
    
    async def connect_postgres(self):
        postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://anomaly_user:anomaly_password@postgres:5432/logsanomaly")
        self.postgres_pool = await asyncpg.create_pool(postgres_dsn)
        print("✅ PostgreSQL conectado")
    
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
