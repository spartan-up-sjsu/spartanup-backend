from fastapi import WebSocket, status
from typing import Optional, Dict, Any, Callable, Awaitable
import asyncio
import json
from app.config import logger
from app.core.security import verify_access_token, decrypt_payload

class AuthenticatedWebSocket:
    """A wrapper around the FastAPI WebSocket that handles authentication and timeout."""
    
    def __init__(self, websocket: WebSocket, auth_timeout: int = 15):
        self.websocket = websocket
        self.auth_timeout = auth_timeout
        self.user_id: Optional[str] = None
        self.authenticated = False
        self.timeout_task: Optional[asyncio.Task] = None
        self.closed = False
    
    async def accept(self):
        """Accept the WebSocket connection and start the authentication timeout."""
        await self.websocket.accept()
        logger.debug("WebSocket connection accepted successfully")
        
        # Start the authentication timeout
        self.timeout_task = asyncio.create_task(self._authentication_timeout())
        
        # Try to authenticate with token in query params
        token = self.websocket.query_params.get("token")
        if token:
            token_preview = token[:20] + "..." if len(token) > 20 else token
            logger.debug(f"WebSocket connection with token: {token_preview}")
            await self.authenticate(token)
    
    async def authenticate(self, token: str) -> bool:
        """Authenticate the WebSocket connection using the provided token."""
        try:
            # Try to decrypt the token first
            payload = decrypt_payload(token)
            if not payload:
                logger.error("Failed to decrypt token payload")
                await self.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token format")
                return False
            
            logger.debug(f"Token payload: {payload}")
            
            # Verify the token
            user_id = verify_access_token(token)
            if not user_id:
                logger.error("WebSocket connection rejected: Invalid token")
                await self.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return False
            
            logger.info(f"WebSocket token verified successfully for user {user_id}")
            
            # Mark as authenticated
            self.user_id = user_id
            self.authenticated = True
            
            # Cancel the timeout task
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
            
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            await self.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication error")
            return False
    
    async def _authentication_timeout(self):
        """Close the connection if authentication doesn't complete within the timeout period."""
        try:
            await asyncio.sleep(self.auth_timeout)
            if not self.authenticated and not self.closed:
                logger.warning(f"WebSocket authentication timeout after {self.auth_timeout} seconds")
                await self.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
        except asyncio.CancelledError:
            # This is expected when authentication succeeds
            pass
        except Exception as e:
            logger.error(f"Error in authentication timeout: {str(e)}")
    
    async def close(self, code: int = status.WS_1000_NORMAL_CLOSURE, reason: str = "Connection closed"):
        """Close the WebSocket connection."""
        if not self.closed:
            try:
                await self.websocket.close(code=code, reason=reason)
                self.closed = True
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
    
    async def receive_text(self) -> str:
        """Receive text from the WebSocket."""
        return await self.websocket.receive_text()
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON from the WebSocket."""
        text = await self.receive_text()
        return json.loads(text)
    
    async def send_text(self, data: str):
        """Send text to the WebSocket."""
        await self.websocket.send_text(data)
    
    async def send_json(self, data: Dict[str, Any]):
        """Send JSON to the WebSocket."""
        await self.websocket.send_json(data)
    
    async def handle_messages(self, message_handler: Callable[[Dict[str, Any], 'AuthenticatedWebSocket'], Awaitable[None]]):
        """Handle incoming messages using the provided message handler."""
        try:
            while True:
                # Wait for messages
                data = await self.receive_text()
                logger.debug(f"Received WebSocket message: {data[:100]}...")
                
                # Try to parse the message as JSON
                try:
                    message = json.loads(data)
                    
                    # Check if this is an authentication message
                    if not self.authenticated and message.get("type") == "authenticate" and "token" in message:
                        authenticated = await self.authenticate(message["token"])
                        if not authenticated:
                            break
                    elif self.authenticated:
                        # Handle the message with the provided handler
                        await message_handler(message, self)
                    else:
                        logger.warning("Received message before authentication")
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {data[:50]}...")
                    
        except Exception as e:
            logger.error(f"Error handling WebSocket messages: {str(e)}")
            await self.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")
