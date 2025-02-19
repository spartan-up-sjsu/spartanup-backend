from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.config import items_collection
from app.schemas.item_schema import list_serialize_items
from bson import ObjectId
from app.models.item_model import ItemRead, ItemFromDB
from fastapi import File, UploadFile
import cloudinary.uploader


async def upload_image(image_data: bytes) -> str:
    result = cloudinary.uploader.upload(image_data)
    return result["secure_url"]


router = APIRouter()


@router.get("/")
async def get_items():
    items = list_serialize_items(items_collection.find())
    return items


@router.get("/{item_id}")
async def get_item(item_id: str):
    item = items_collection.find_one({"_id": ObjectId(item_id)})
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemRead(**item)


# TODO: make this a multipart request so that we can upload images.
@router.post("/")
async def create_item(item: ItemRead, files: List[UploadFile] = File(...)):
    images = []
    for file in files:
        image_data = await file.read()
        image_url = await upload_image(image_data)
        images.append(image_url)
    item.images = images
    items_collection.insert_one(item.model_dump())


@router.put("/{item_id}")
async def update_item(item_id: str):
    # TODO: Implement update item
    pass


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    # TODO: Implement delete item
    pass
