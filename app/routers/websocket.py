from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from app.config import messages_collection
from app.websocket_manager import ws_manager

router = APIRouter()

active_connections = set()

@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)