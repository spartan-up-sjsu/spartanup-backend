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
        self.active_connections: dict[str, list[WebSocket]] = {}  # Stores WebSockets per conversation_id

    async def connect(self, websocket: WebSocket, conversation_id: str):
        """ Adds a new WebSocket connection to the conversation """
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
        print(f"WebSocket connected for conversation {conversation_id}")

    async def disconnect(self, conversation_id: str, websocket: WebSocket):
        """ Removes WebSocket connection when a user disconnects """
        if conversation_id in self.active_connections:
            try:
                self.active_connections[conversation_id].remove(websocket)
                if not self.active_connections[conversation_id]:  # If empty, remove the conversation
                    del self.active_connections[conversation_id]
            except ValueError:
                pass

    async def broadcast(self, conversation_id: str, message: dict, sender_websocket: WebSocket):
        """ Sends message to all users in the conversation except the sender """
        if conversation_id in self.active_connections:
            disconnected_clients = []
            
            for websocket in self.active_connections[conversation_id]:
                if websocket != sender_websocket:  # Don't send message back to sender
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        print(f"Failed to send message: {e}")
                        disconnected_clients.append(websocket)

            # Clean up disconnected clients
            for client in disconnected_clients:
                await self.disconnect(conversation_id, client)


manager = ConnectionManager()


@router.websocket("/")
async def websocket_chat(websocket: WebSocket):
    """ Handles WebSocket connections and real-time chat messaging """
    try:
        await websocket.accept()

        # Receive first message containing conversation_id & user_id
        initial_message = await websocket.receive_text()
        try:
            initial_data = json.loads(initial_message)
            conversation_id = initial_data.get("conversation_id")
            user_id = initial_data.get("sent_by")
        except json.JSONDecodeError:
            await websocket.send_json({"error": "Invalid JSON format"})
            await websocket.close()
            return

        if not conversation_id or not user_id:
            await websocket.send_json({"error": "Missing conversation_id or user_id"})
            await websocket.close()
            return

        await manager.connect(websocket, conversation_id)
        print(f"User {user_id} connected to conversation {conversation_id}")

        while True:
            message_data = await websocket.receive_text()
            
            try:
                data = json.loads(message_data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue  

            message_type = data.get("type")

            if message_type == "chat":
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

                    # Send message to all users in conversation except sender
                    await manager.broadcast(conversation_id, {
                        "type": "chat",
                        **message
                    }, sender_websocket=websocket)

            elif message_type == "fetch_past":
                past_messages = list(messages_collection.find({"conversation_id": conversation_id}))
                for msg in past_messages:
                    msg["_id"] = str(msg["_id"])
                    if isinstance(msg["created_at"], datetime):
                        msg["created_at"] = msg["created_at"].isoformat()

                await websocket.send_json({"type": "past_messages", "messages": past_messages})

            elif message_type == "typing":
                await manager.broadcast(conversation_id, {
                    "type": "typing",
                    "sent_by": user_id
                }, sender_websocket=websocket)

            elif message_type == "read_receipt":
                await manager.broadcast(conversation_id, {
                    "type": "read_receipt",
                    "sent_by": user_id,
                    "conversation_id": conversation_id
                }, sender_websocket=websocket)

            else:
                await websocket.send_json({"error": "Unknown message type"})

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected from conversation {conversation_id}")
        await manager.disconnect(conversation_id, websocket)

    except Exception as e:
        print(f"Unexpected error: {e}")
        await websocket.send_json({"error": "Server error"})
        await websocket.close()
