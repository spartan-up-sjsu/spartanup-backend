from fastapi import Request, HTTPException, Depends
from app.core.security import verify_access_token  # Make sure to import your function
from fastapi.responses import RedirectResponse


def get_current_user_id(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = verify_access_token(token)
    if not user_id:
        return RedirectResponse(url="/login")
    return user_id
