from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from app.websockets.manager import ws_manager
from app.config import logger
from typing import Dict, Any

router = APIRouter()

async def message_handler(message: Dict[str, Any], connection):
    """Handle authenticated messages from WebSocket clients."""
    logger.info(f"Handling message from user {connection.user_id}: {message.get('type', 'unknown')}")
    
    # Handle different message types
    msg_type = message.get("type")
    
    if msg_type == "ping":
        # Simple ping-pong for connection testing
        await connection.send_json({"type": "pong"})
    
    elif msg_type == "message" and "content" in message:
        # Echo the message back for now
        await connection.send_json({
            "type": "message",
            "from": connection.user_id,
            "content": message["content"]
        })

@router.websocket("")  # This will match /ws when mounted with prefix
async def websocket_endpoint_root(websocket: WebSocket):
    """WebSocket endpoint for the /ws path."""
    logger.debug("WebSocket connection attempt at /ws")
    await ws_manager.handle_connection(websocket, message_handler)

@router.websocket("/")  # This will match /ws/ when mounted with prefix
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for the /ws/ path."""
    logger.debug("WebSocket connection attempt at /ws/")
    await ws_manager.handle_connection(websocket, message_handler)