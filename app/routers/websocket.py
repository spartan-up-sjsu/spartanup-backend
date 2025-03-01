from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from typing import List
import asyncio

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        asyncio.create_task(self.ping_client(websocket))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Failed to send: {e}")
                disconnected_clients.append(connection)

        for client in disconnected_clients:
            self.disconnect(client)

    async def ping_client(self, websocket: WebSocket):
        try:
            while websocket in self.active_connections:
                await websocket.send_bytes(b"ping")  
                await asyncio.sleep(10)
        except WebSocketDisconnect:
            print("Client disconnected due to ping timeout")
            self.disconnect(websocket)
        except Exception as e:
            print(f"Ping error: {e}")
            self.disconnect(websocket)

manager = ConnectionManager()

@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from {client_id}: {data}")
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} has left")
