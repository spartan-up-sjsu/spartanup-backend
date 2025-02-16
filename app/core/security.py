import jwt
from datetime import datetime, timedelta
from ..config import settings


def create_access_token(email: str, expires_delta: int = 60):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(minutes=expires_delta),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        # Handle token expiration
        return None
    except jwt.JWTError:
        # Handle other JWT errors
        return None
