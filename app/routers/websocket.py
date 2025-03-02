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
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()

        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
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
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    conversations_collection.insert_one(conversation)
    return {"conversationId": conversation_id}

@router.websocket("/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    try:
        conversation = conversations_collection.find_one({"_id": ObjectId(conversation_id)})

        if not conversation:
            await websocket.send_text("Error: Conversation not found")
            await websocket.close()
            return

        buyer_id = str(conversation["buyer_id"])  # Convert ObjectId to string
        seller_id = str(conversation["seller_id"])

        await manager.connect(websocket, conversation_id)  # Ensure correct number of arguments

        while True:
            message_data = await websocket.receive_text()
            message_json = json.loads(message_data)

            sent_by = str(message_json.get("sent_by"))
            content = message_json.get("content")

            if sent_by not in [buyer_id, seller_id]:
                await websocket.send_text("Error: Invalid sender")
                continue

            message = {
                "conversation_id": ObjectId(conversation_id),  # Store as ObjectId
                "content": content,
                "sent_by": sent_by,
                "created_at": datetime.utcnow(),
            }
            print("Saving message:", message)  # Debugging line
            messages_collection.insert_one(message)
            print("Message saved successfully!")

            await manager.broadcast(message, str(conversation_id))  # Convert ObjectId to string

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")
