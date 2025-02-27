import jwt
from datetime import datetime, timedelta
from ..config import settings
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from datetime import timezone

# Generate a Fernet key from the SECRET_KEY
def get_fernet_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"spartanup_static_salt",  # Using a static salt since we want the same key each time
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return Fernet(key)

def encrypt_payload(payload: dict) -> str:
    """Encrypt the JWT payload using Fernet"""
    f = get_fernet_key()
    payload_bytes = jwt.encode(payload, "", algorithm="none").encode()
    return f.encrypt(payload_bytes).decode()

def decrypt_payload(token: str) -> dict:
    """Decrypt the JWT payload using Fernet"""
    f = get_fernet_key()
    try:
        decrypted = f.decrypt(token.encode())
        return jwt.decode(decrypted, "", algorithms=["none"])
    except Exception:
        return None

def create_access_token(email: str, expires_delta: int = 60):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_delta),
        "type": "access"
    }
    return encrypt_payload(payload)

def create_refresh_token(email: str, expires_delta: int = 60 * 24 * 7):  # 7 days default
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_delta),
        "type": "refresh"
    }
    return encrypt_payload(payload)

def verify_token(token: str, token_type: str = None):
    try:
        payload = decrypt_payload(token)
        if not payload:
            return None
            
        # Check expiration
        exp = datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
        if datetime.now(datetime.timezone.utc) >= exp:
            return None
            
        # Verify token type if specified
        if token_type and payload.get("type") != token_type:
            return None
            
        return payload.get("sub")
    except Exception:
        return None

def verify_access_token(token: str):
    return verify_token(token, "access")

def verify_refresh_token(token: str):
    return verify_token(token, "refresh")
