import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
import aioredis
from fastapi import WebSocket

class StreamManager:
    """Gestiona streams de resultados usando Redis Pub/Sub"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self._active_connections: Dict[str, Dict[str, WebSocket]] = {}
        
    async def register_connection(self, job_id: str, client_id: str, websocket: WebSocket):
        """Registra una nueva conexión WebSocket"""
        if job_id not in self._active_connections:
            self._active_connections[job_id] = {}
        self._active_connections[job_id][client_id] = websocket
        
        # Crear canal dedicado para este job
        channel_name = f"stream:job:{job_id}"
        
        # Publicar estado actual del job
        current_state = await self._get_current_state(job_id)
        await websocket.send_json(current_state)
    
    async def unregister_connection(self, job_id: str, client_id: str):
        """Elimina una conexión WebSocket"""
        if job_id in self._active_connections:
            self._active_connections[job_id].pop(client_id, None)
            if not self._active_connections[job_id]:
                del self._active_connections[job_id]
    
    async def publish_update(self, job_id: str, data: Dict[str, Any]):
        """Publica una actualización a todos los clientes de un job"""
        channel_name = f"stream:job:{job_id}"
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Publicar en Redis
        await self.redis.publish(channel_name, json.dumps(message))
        
        # Actualizar cache de estado
        await self._update_state_cache(job_id, data)
    
    async def start_listening(self, job_id: str, client_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Generator para escuchar actualizaciones de un job"""
        channel_name = f"stream:job:{job_id}"
        pubsub = self.redis.pubsub()
        
        try:
            await pubsub.subscribe(channel_name)
            
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message:
                        data = json.loads(message["data"])
                        yield data
                    else:
                        # Verificar si el job ha terminado
                        if await self._is_job_completed(job_id):
                            break
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    print(f"Error en stream de job {job_id}: {str(e)}")
                    await asyncio.sleep(1)
                    
        finally:
            await pubsub.unsubscribe(channel_name)
    
    async def _get_current_state(self, job_id: str) -> Dict[str, Any]:
        """Obtiene el estado actual del job desde Redis"""
        state = await self.redis.get(f"state:job:{job_id}")
        return json.loads(state) if state else {"status": "unknown"}
    
    async def _update_state_cache(self, job_id: str, data: Dict[str, Any]):
        """Actualiza el cache de estado en Redis"""
        await self.redis.setex(
            f"state:job:{job_id}",
            3600,  # TTL: 1 hora
            json.dumps(data)
        )
    
    async def _is_job_completed(self, job_id: str) -> bool:
        """Verifica si un job ha terminado"""
        state = await self._get_current_state(job_id)
        return state.get("status") in ["completed", "failed"]
