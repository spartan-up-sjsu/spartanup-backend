from fastapi import APIRouter, Depends, HTTPException
from ..schemas.user_schema import UserLogin
from ..core import security

router = APIRouter()


@router.post("/login")
async def login(user_data: UserLogin):
    # 1. Validate user credentials.
    # 2. Create and return JWT token if credentials are valid.
    # 3. Otherwise, raise 401 Unauthorized.
    token = security.create_access_token(user_data.email)
    return {"access_token": token}
