from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.config import logger
from ..models.user_model import UserCreate, UserRead
from fastapi import Request
from app.core.security import verify_access_token
from ..config import user_collection, items_collection
from bson import ObjectId

router = APIRouter()

@router.get("/@me")
async def read_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = verify_access_token(token)
        user = user_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        items = items_collection.find_one({"seller_id": ObjectId(user_id)})
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token verification failed")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user": user, "items": items} 



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
