from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import uuid
from services.stream_manager import StreamManager

router = APIRouter()
stream_manager = None  # Se inicializa en startup

@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """Endpoint WebSocket para streaming de resultados"""
    client_id = str(uuid.uuid4())
    
    try:
        await websocket.accept()
        await stream_manager.register_connection(job_id, client_id, websocket)
        
        async for update in stream_manager.start_listening(job_id, client_id):
            await websocket.send_json(update)
            
    except WebSocketDisconnect:
        await stream_manager.unregister_connection(job_id, client_id)
    except Exception as e:
        print(f"Error en WebSocket {client_id}: {str(e)}")
        await stream_manager.unregister_connection(job_id, client_id)
        if not websocket.client_state.disconnected:
            await websocket.close()
