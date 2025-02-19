from fastapi import APIRouter, Depends, HTTPException, Form
from typing import List
from app.config import items_collection
from app.schemas.item_schema import list_serialize_items
from bson import ObjectId
from app.models.item_model import ItemRead, ItemFromDB
from fastapi import File, UploadFile
from app.config import upload_image
import cloudinary.uploader
import json


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


@router.post("/")
async def create_item(item: str = Form(...), files: List[UploadFile] = File(...)):
    images = []
    item_data = json.loads(item)
    for file in files:
        print("uploading image")
        image_data = await file.read()
        image_url = await upload_image(image_data)
        images.append(image_url)
        print("image uploaded", image_url)
    item_data["images"] = images
    items_collection.insert_one(item_data)
    print("item created", item_data)
    return {"message": "Item created successfully"}


@router.put("/{item_id}")
async def update_item(item_id: str):
    # TODO: Implement update item
    pass


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    # TODO: Implement delete item
    pass
