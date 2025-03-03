from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from typing import List
import asyncio
from app.config import conversations_collection, messages_collection
from app.models.conversation_model import Conversation, ChatRequest
from app.models.message_model import Message
from bson import ObjectId
import json
from datetime import datetime

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {} 

    async def connect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
        asyncio.create_task(self.ping_client(websocket))

    async def disconnect(self, conversation_id: str, websocket: WebSocket):
        if conversation_id in self.active_connections:
            try:
                self.active_connections[conversation_id].remove(websocket) 
                if not self.active_connections[conversation_id]:  
                    del self.active_connections[conversation_id]
            except ValueError:
                pass 

    async def send_message(self, conversation_id: str, content: str):
        disconnected_clients = []
        
        if conversation_id not in self.active_connections:
            return

        for websocket in self.active_connections[conversation_id]:
            try:
                await websocket.send_text(content)  
            except Exception as e:
                print(f"Failed to send message: {e}")
                disconnected_clients.append(websocket)

        for client in disconnected_clients:
            self.disconnect(conversation_id, client)

    async def ping_client(self, websocket: WebSocket):
        try:
            while True:
                await websocket.send_bytes(b"ping")
                await asyncio.sleep(10)
        except WebSocketDisconnect:
            print("Client disconnected due to ping timeout")
        except Exception as e:
            print(f"Ping error: {e}")
    
    async def broadcast(self, conversation_id: str, message: dict):
        if conversation_id in self.active_connections:
            for ws in self.active_connections[conversation_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"Failed to send message: {e}")
                    await self.disconnect(conversation_id, ws) 


manager = ConnectionManager()

@router.websocket("/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    try:
        await websocket.accept()

        past_messages = list(messages_collection.find({"conversation_id": conversation_id}))
        for msg in past_messages:
            msg["_id"] = str(msg["_id"]) 
            if isinstance(msg["created_at"], datetime):
                msg["created_at"] = msg["created_at"].isoformat()

        await websocket.send_json({"type": "past_messages", "messages": past_messages})

        message_data = await websocket.receive_text()
        try:
            data = json.loads(message_data)
        except json.JSONDecodeError:
            await websocket.send_json({"error": "Invalid JSON format"})
            await websocket.close()
            return

        user_id = data.get("sent_by")
        if not user_id:
            await websocket.send_json({"error": "Missing user_id"})
            await websocket.close()
            return

        await manager.connect(websocket, conversation_id)

        while True:
            content = data.get("content", "").strip()
            if content:
                message = {
                    "_id": str(ObjectId()),
                    "conversation_id": conversation_id,
                    "sent_by": user_id,
                    "content": content,
                    "created_at": datetime.utcnow().isoformat(),
                }

                messages_collection.insert_one(message)
                await manager.broadcast(conversation_id, message)

            message_data = await websocket.receive_text()
            try:
                data = json.loads(message_data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue  

    except WebSocketDisconnect:
        print("WebSocket disconnected")
        manager.disconnect(conversation_id, websocket)

    except Exception as e:
        print(f"Unexpected error: {e}")
        await websocket.send_json({"error": "Server error"})
        await websocket.close()

