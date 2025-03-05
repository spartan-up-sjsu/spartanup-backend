import jwt
from datetime import datetime, timedelta
from ..config import settings
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..config import logger
from datetime import timezone

# Generate a Fernet key from the SECRET_KEY
def get_secret_key() -> str:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"spartanup_static_salt",  
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key.decode()  


def get_fernet_key() -> Fernet:
    secret_key = get_secret_key().encode()  

    return Fernet(secret_key)



def encrypt_payload(payload: dict) -> str:
    secret = get_secret_key()
    token = jwt.encode(payload, secret, algorithm="HS256")
    # if isinstance(token, bytes):
    #     token = token.decode("utf-8")
    f = get_fernet_key()
    encrypted = f.encrypt(token.encode())
    return encrypted.decode()



def decrypt_payload(token: str) -> dict:

    f = get_fernet_key()
    try:
        decrypted = f.decrypt(token.encode()).decode()
        secret = get_secret_key()
        payload = jwt.decode(decrypted, secret, algorithms=["HS256"])
        return payload
    except Exception as e:
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
            logger.error("Payload is empty")
            return None
            
        # Check expiration
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if datetime.now(timezone.utc) >= exp:
            logger.error("Token has expired")
            return None
            
        # Verify token type if specified
        if token_type and payload.get("type") != token_type:
            logger.error(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None
            
        return payload.get("sub")
    except Exception as e:
        logger.error(f"Token verification exception: {str(e)}")
        return None



def verify_access_token(token: str):
    return verify_token(token, "access")

def verify_refresh_token(token: str):
    return verify_token(token, "refresh")


