from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter()


@router.get("/")
async def get_items():
    # TODO: Implement get all items
    return []


@router.get("/{item_id}")
async def get_item(item_id: str):
    # TODO: Implement get single item
    pass


@router.post("/")
async def create_item():
    # TODO: Implement create item
    pass


@router.put("/{item_id}")
async def update_item(item_id: str):
    # TODO: Implement update item
    pass


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    # TODO: Implement delete item
    pass
