from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from app.config import messages_collection

router = APIRouter()

active_connections = set()

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event = message.get("event")
            conversation_id = message.get("conversation_id")
            sent_by = message.get("sent_by")
            content = message.get("content")
            created_at = message.get("created_at")

            messages_collection.insert_one({
                "event": event,
                "conversation_id": conversation_id,
                "sent_by": sent_by,
                "content": content,
                "created_at": created_at
            })

            response = {
                "event": event,
                "conversation_id": conversation_id,
                "sent_by": sent_by,
                "content": content,
                "created_at": created_at,
                "message": f"Saved {event} event."
            }

            for connection in active_connections:
                await connection.send_text(json.dumps(response))

    except WebSocketDisconnect:
        active_connections.remove(websocket)
