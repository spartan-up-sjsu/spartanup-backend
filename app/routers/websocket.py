from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from app.websockets.manager import ws_manager
from app.config import logger
from typing import Dict, Any

router = APIRouter()

async def message_handler(message: Dict[str, Any], connection):
    """Handle authenticated messages from WebSocket clients."""
    logger.info(f"Handling message from user {connection.user_id}: {message.get('type', 'unknown')}")
    
    try:
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
        
        elif msg_type == "message" and message.get("channel") == "typing":
            # Handle typing indicator events
            data = message.get("data", {})
            conversation_id = data.get("conversation_id")
            user_id = data.get("user_id")
            is_typing = data.get("is_typing", False)
            user_name = data.get("user_name", "")
            
            if not conversation_id or not user_id:
                logger.warning("Received typing event with missing conversation_id or user_id")
                return
                
            typing_event = {
                "type": "typing_indicator",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "is_typing": is_typing,
                "user_name": user_name
            }
            
            # Use the conversation-specific broadcast method
            await ws_manager.broadcast_to_conversation(
                conversation_id, 
                typing_event, 
                exclude=connection.user_id
            )
            
            logger.info(f"User {user_name} ({user_id}) typing status in conversation {conversation_id}: {is_typing}")
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {str(e)}")
        # Send error message to the client
        await connection.send_json({
            "type": "error",
            "message": "Failed to process your message"
        })

@router.websocket("")  # This will match /ws when mounted with prefix
async def websocket_endpoint_root(websocket: WebSocket):
    """WebSocket endpoint for the /ws path."""
    logger.debug("WebSocket connection attempt at /ws")
    await ws_manager.handle_connection(websocket, message_handler)