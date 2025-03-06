from fastapi import Request, HTTPException, Depends
from app.core.security import verify_access_token  # Make sure to import your function

def get_current_user(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_email = verify_access_token(token)
    if not user_email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_email
