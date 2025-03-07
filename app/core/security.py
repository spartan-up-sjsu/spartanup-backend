import jwt
import base64
from datetime import datetime, timedelta, timezone
from app.config import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger("app")

# Derive a secret key as a string for JWT signing.
def get_secret_key() -> str:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"spartanup_static_salt",  # Fixed salt for consistency
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key.decode()  # Return as a string

# Create a Fernet instance for encryption/decryption.
def get_fernet_key() -> Fernet:
    # We use the same derived key (as bytes) for Fernet.
    secret_str = get_secret_key()  # This is a string.
    secret_bytes = secret_str.encode("utf-8")  # Convert to bytes.
    # Use the same key for Fernet (Fernet expects a base64-encoded 32-byte key)
    return Fernet(secret_bytes)

# This function signs the payload with JWT and then encrypts the resulting token using Fernet.
def encrypt_payload(payload: dict) -> str:
    secret = get_secret_key()
    # Sign the payload with HS256.
    token = jwt.encode(payload, secret, algorithm="HS256")
    # Ensure token is a string.
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    # Now encrypt the JWT token using Fernet.
    f = get_fernet_key()
    encrypted = f.encrypt(token.encode("utf-8"))
    return encrypted.decode("utf-8")

# This function decrypts the token using Fernet and then decodes the JWT to get the payload dictionary.
def decrypt_payload(token: str) -> dict:
    f = get_fernet_key()
    try:
        # Decrypt the token and decode it to a UTF-8 string.
        decrypted_token = f.decrypt(token.encode("utf-8")).decode("utf-8")
        secret = get_secret_key()
        payload = jwt.decode(decrypted_token, secret, algorithms=["HS256"])
        return payload
    except Exception as e:
        logger.error(f"Error during decryption: {str(e)}")
        return None


# Create an access token that expires after 'expires_delta' minutes.
def create_access_token(email: str, expires_delta: int = 60) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    payload = {
        "sub": email,
        "exp": expire.timestamp(),  # Store expiration as a UNIX timestamp
        "type": "access"
    }
    return encrypt_payload(payload)

# Create a refresh token that expires after 7 days by default.
def create_refresh_token(email: str, expires_delta: int = 60 * 24 * 7) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    payload = {
        "sub": email,
        "exp": expire.timestamp(),
        "type": "refresh"
    }
    return encrypt_payload(payload)

# Verify the token by decrypting it and checking the expiration and token type.
def verify_token(token: str, token_type: str = None) -> str:
    try:
        payload = decrypt_payload(token)
        logger.info(f"Decoded payload: {payload}")
        if not payload:
            return None
            
        # Check expiration.
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if datetime.now(timezone.utc) >= exp:
            logger.error("Token expired")
            return None
            
        # Verify token type if specified.
        if token_type and payload.get("type") != token_type:
            logger.error(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None
            
        return payload.get("sub")
    except Exception as e:
        logger.error(f"Token verification exception: {str(e)}")
        return None

def verify_access_token(token: str) -> str:
    return verify_token(token, "access")

def verify_refresh_token(token: str) -> str:
    return verify_token(token, "refresh")
