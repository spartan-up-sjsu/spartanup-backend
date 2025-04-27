from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.config import logger
from ..models.user_model import UserCreate, UserRead
from fastapi import Request
from app.core.security import verify_access_token
from ..config import user_collection, items_collection
from bson import ObjectId
from fastapi import Depends
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
        items = items_collection.find({"seller_id": ObjectId(user_id)})
        items_list = []
        for item in items:
            item["_id"] = str(item["_id"])
            item["seller_id"] = str(item["seller_id"])
            items_list.append(item)
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token verification failed")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user": user, "items_list": items_list} 



@router.get("/", response_model=List[UserRead])
async def get_users():
    # TODO: 
    return []


@router.get("/{user_id}")
async def get_user(user_id: str):
    try:
        logger.info(f"Finding user in MongoDB with ID: {user_id}")
        object_id = ObjectId(user_id) 
        user = user_collection.find_one({"_id": object_id})
        if user is None:
            logger.error("Unable to find user")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info("Fetching user")
        user['_id'] = str(user['_id'])
        return {"message": "User retrieved successfully", "data": user}
    except errors.InvalidId: 
        logger.error(f"Invalid ObjectId format: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except Exception as e:
        logger.error(f"Unexpected error retrieving user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
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
