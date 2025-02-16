from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.user_model import UserCreate, UserRead

router = APIRouter()


@router.get("/", response_model=List[UserRead])
async def get_users():
    # TODO: Implement get all users
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
