from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected to WebSocket.") 

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        print(f"User {user_id} disconnected.") 

    async def send_message(self, recipient_id: str, message: dict):
        if recipient_id in self.active_connections:
            await self.active_connections[recipient_id].send_json(message)
            print(f"Sending WebSocket message to {recipient_id}: {message}")  # Debugging log

ws_manager = WebSocketManager()
