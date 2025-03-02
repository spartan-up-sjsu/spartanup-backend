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
        await websocket.accept()

        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
        asyncio.create_task(self.ping_client(websocket))

    def disconnect(self, conversation_id: str, websocket: WebSocket):
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


manager = ConnectionManager()

@router.post("/chat")
async def create_or_get_chat(request: ChatRequest):
    item_id = ObjectId(request.item_id)
    buyer_id = ObjectId(request.buyer_id)
    seller_id = ObjectId(request.seller_id)

    existing_chat = conversations_collection.find_one({
        "item_id": item_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
    }) 
    if existing_chat:
        return {"conversationId": str(existing_chat["_id"])}
    
    conversation_id = str(ObjectId())
    conversation = {
        "_id": ObjectId(conversation_id),
        "item_id": item_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    conversations_collection.insert_one(conversation)
    return {"conversationId": conversation_id}

@router.websocket("/{conversation_id}/{user_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str, user_id: str):
    try:
        await manager.connect(websocket, conversation_id) 

        conversation = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
        if not conversation:
            await websocket.send_json({"error": "Conversation not found"})
            await websocket.close()
            return

        buyer_id = str(conversation["buyer_id"])
        seller_id = str(conversation["seller_id"])

        if user_id not in [buyer_id, seller_id]:
            await websocket.send_json({"error": "Unauthorized user"})
            await websocket.close()
            return
        
        past_messages = list(messages_collection.find({"conversation_id": conversation_id}))

        for msg in past_messages:
            msg["_id"] = str(msg["_id"])
            if isinstance(msg["created_at"], datetime):  
                msg["created_at"] = msg["created_at"].isoformat()

        await websocket.send_json({"type": "past_messages", "messages": past_messages})

        while True:
            message_data = await websocket.receive_text()
            content = message_data.strip()

            message = {
                "_id": str(ObjectId()),
                "conversation_id": conversation_id,
                "sent_by": user_id,
                "content": content,  
                "created_at": datetime.utcnow().isoformat(),
            }
            messages_collection.insert_one(message) 

            await manager.send_message(conversation_id, content)

    except WebSocketDisconnect:
        print(f"🔻 WebSocket disconnected for user: {user_id}")
        await manager.disconnect(conversation_id, websocket)
