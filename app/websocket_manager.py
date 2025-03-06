from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, buyer_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[buyer_id] = websocket

    def disconnect(self, buyer_id: str):
        self.active_connections.pop(buyer_id, None)

    async def send_message(self, recipient_id: str, message: dict):
        if recipient_id in self.active_connections:
            await self.active_connections[recipient_id].send_json(message)

ws_manager = WebSocketManager()
