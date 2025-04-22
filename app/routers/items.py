from fastapi import APIRouter, Depends, HTTPException, Form, Request
from typing import List
from app.config import items_collection, user_collection
from app.schemas.item_schema import list_serialize_items
from bson import ObjectId, errors
from app.models.item_model import ItemRead, ItemFromDB, ItemCreate
from fastapi import File, UploadFile
from app.config import upload_image
from app.config import logger
import cloudinary.uploader
import json
from typing import Optional
from app.core.security import verify_access_token

router = APIRouter()

@router.get("/")
async def get_items():
    try: 
        logger.info("Retrieving all items from mongodb")
        items = list_serialize_items(items_collection.find())
        return {"message": "Items retrieved successfully", "data": items}
    except Exception as e: 
        logger.error("Unable to retrieve items" + str(e))
        raise HTTPException(status_code=404, detail="Cannot retrieve items")

@router.get("/{item_id}") 
async def get_item(item_id: str):
    try:
        logger.info(f"Finding item in MongoDB with ID: {item_id}")
        object_id = ObjectId(item_id) 
        item = items_collection.find_one({"_id": object_id})
        if item is None:
            logger.error("Unable to find item")
            raise HTTPException(status_code=404, detail="Item not found")
        logger.info("Fetching item")
        item['_id'] = str(item['_id'])
        item['seller_id'] = str(item['seller_id'])
        return {"message": "Item retrieved successfully", "data": item}
    except errors.InvalidId: 
        logger.error(f"Invalid ObjectId format: {item_id}")
        raise HTTPException(status_code=400, detail="Invalid item ID format")
    except Exception as e:
        logger.error(f"Unexpected error retrieving item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



@router.post("/")
async def create_item(item: str = Form(...), files: List[UploadFile] = File(...)):
    try: 
        logger.info("Creating items")
        images = []
        item_data = json.loads(item)
        validated_item = ItemCreate(**item_data)
        for file in files:
            logger.info("Uploading image to cloudinary")
            image_data = await file.read()
            image_url = await upload_image(image_data)
            images.append(image_url)
            logger.info("Image uploaded")
        validated_item_dict = validated_item.model_dump()
        validated_item_dict["images"] = images
        validated_item_dict["seller_id"] = ObjectId(validated_item_dict["sellerId"])
        logger.info("Inserting item to mongodb")
        items_collection.insert_one(validated_item_dict)
        return {"message": "Item created successfully"}
    except json.JSONDecodeError as e: 
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format" + str(e)) 
    except Exception as e:
        logger.error("Error creating item" + str(e)) 
        raise HTTPException(status_code=500, detail="Cannot create item")
    
@router.delete("/{item_id}")
async def delete_item(item_id: str):
    try:
        logger.info(f"Deleting item with ID: {item_id}")
        result = items_collection.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            logger.error("Item not found")
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Item deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        raise HTTPException(status_code=500, detail="Cannot delete item")
