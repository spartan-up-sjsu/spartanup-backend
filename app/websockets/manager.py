from fastapi import WebSocket
from typing import Dict, Optional, Callable, Awaitable, Any
from app.websockets.connection import AuthenticatedWebSocket
from app.config import logger

class WebSocketManager:
    """Manages all active WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, AuthenticatedWebSocket] = {}
    
    async def create_connection(self, websocket: WebSocket) -> AuthenticatedWebSocket:
        """Create and accept a new WebSocket connection."""
        connection = AuthenticatedWebSocket(websocket)
        await connection.accept()
        return connection
    
    def register_connection(self, user_id: str, connection: AuthenticatedWebSocket):
        """Register an authenticated connection."""
        # Remove any existing connection for this user
        if user_id in self.active_connections:
            logger.info(f"Replacing existing WebSocket connection for user {user_id}")
        
        self.active_connections[user_id] = connection
        logger.info(f"User {user_id} connected to WebSocket")
    
    def disconnect(self, user_id: str):
        """Remove a connection from active connections."""
        if user_id in self.active_connections:
            self.active_connections.pop(user_id, None)
            logger.info(f"User {user_id} disconnected")
    
    async def send_message(self, recipient_id: str, message: Dict[str, Any]):
        """Send a message to a specific user."""
        if recipient_id in self.active_connections:
            await self.active_connections[recipient_id].send_json(message)
            logger.info(f"Sent message to user {recipient_id}")
            return True
        logger.warning(f"Failed to send message: User {recipient_id} not connected")
        return False
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[str] = None):
        """Broadcast a message to all connected users except the excluded one."""
        for user_id, connection in self.active_connections.items():
            if exclude is None or user_id != exclude:
                await connection.send_json(message)
        
        logger.info(f"Broadcast message to {len(self.active_connections) - (1 if exclude else 0)} users")
    
    async def handle_connection(self, websocket: WebSocket, 
                               message_handler: Callable[[Dict[str, Any], AuthenticatedWebSocket], Awaitable[None]]):
        """Handle a WebSocket connection from start to finish."""
        connection = await self.create_connection(websocket)
        
        try:
            # Wait for authentication and handle messages
            await connection.handle_messages(message_handler)
        finally:
            # Clean up when the connection is closed
            if connection.authenticated and connection.user_id:
                self.disconnect(connection.user_id)
            
            # Make sure the connection is closed
            await connection.close()

# Global WebSocket manager instance
ws_manager = WebSocketManager()
