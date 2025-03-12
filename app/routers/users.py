from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.config import logger
from ..models.user_model import UserCreate, UserRead
from fastapi import Request
from app.core.security import verify_access_token


router = APIRouter()

@router.get("/@me")
async def read_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_email = verify_access_token(token)

    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token verification failed")
    if not user_email:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"email": user_email} #


@router.get("/", response_model=List[UserRead])
async def get_users():
    # TODO: 
    return []


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str):
    # TODO: Implement get single user
    pass


@router.post("/", response_model=UserRead)
async def create_user(user: UserCreate):
    # TODO: Implement create user
    pass


@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: str):
    # TODO: Implement update user
    pass


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    # TODO: Implement delete user
    pass
