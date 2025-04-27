from fastapi import WebSocket, WebSocketDisconnect, status
from typing import Dict, Optional
import asyncio
from app.config import logger
from app.core.security import verify_access_token, decrypt_payload

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_connections: Dict[WebSocket, asyncio.Task] = {}
        self.auth_timeout = 15  # 15 seconds timeout for authentication

    async def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id] = websocket
        
        # If this websocket was in pending connections, remove it and cancel the timeout task
        if websocket in self.pending_connections:
            timeout_task = self.pending_connections.pop(websocket)
            if not timeout_task.done():
                timeout_task.cancel()
        
        logger.info(f"User {user_id} connected to WebSocket.")

    async def accept_connection(self, websocket: WebSocket):
        """Accept a WebSocket connection and start the authentication timeout."""
        try:
            await websocket.accept()
            logger.debug("WebSocket connection accepted successfully")
            
            # Create a timeout task for this connection
            timeout_task = asyncio.create_task(self._authentication_timeout(websocket))
            self.pending_connections[websocket] = timeout_task
            
            # Extract token from query params for debugging
            token = websocket.query_params.get("token")
            if token:
                token_preview = token[:20] + "..." if len(token) > 20 else token
                logger.debug(f"WebSocket connection with token: {token_preview}")
                
                # Immediately try to authenticate with the token
                try:
                    authenticated_user_id = await self.authenticate_connection(websocket, token)
                    if authenticated_user_id:
                        return websocket
                except Exception as e:
                    logger.error(f"Error during immediate authentication: {str(e)}")
            else:
                logger.debug("WebSocket connection without token, waiting for authentication message")
                
            return websocket
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {str(e)}")
            raise

    async def authenticate_connection(self, websocket: WebSocket, token: str) -> Optional[str]:
        """Authenticate a WebSocket connection using the provided token."""
        try:
            # Try to decrypt the token first
            payload = decrypt_payload(token)
            if not payload:
                logger.error("Failed to decrypt token payload")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token format")
                return None
            
            logger.debug(f"Token payload: {payload}")
            
            # Verify the token
            user_id = verify_access_token(token)
            if not user_id:
                logger.error("WebSocket connection rejected: Invalid token")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return None
            
            logger.info(f"WebSocket token verified successfully for user {user_id}")
            
            # Register the authenticated connection
            await self.connect(user_id, websocket)
            return user_id
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication error")
            return None

    async def _authentication_timeout(self, websocket: WebSocket):
        """Close the connection if authentication doesn't complete within the timeout period."""
        await asyncio.sleep(self.auth_timeout)
        if websocket in self.pending_connections:
            logger.warning(f"WebSocket authentication timeout after {self.auth_timeout} seconds")
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
            except Exception as e:
                logger.error(f"Error closing WebSocket on timeout: {str(e)}")
            finally:
                self.pending_connections.pop(websocket, None)

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        logger.info(f"User {user_id} disconnected.")

    def cancel_pending_connection(self, websocket: WebSocket):
        """Cancel a pending connection and its timeout task."""
        if websocket in self.pending_connections:
            timeout_task = self.pending_connections.pop(websocket)
            if not timeout_task.done():
                timeout_task.cancel()

    async def send_message(self, recipient_id: str, message: dict):
        if recipient_id in self.active_connections:
            await self.active_connections[recipient_id].send_json(message)
            logger.info(f"Sending WebSocket message to {recipient_id}: {message}")  # Debugging log

ws_manager = WebSocketManager()
