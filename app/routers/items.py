from fastapi import APIRouter, Depends, HTTPException, Form
from typing import List
from app.config import items_collection
from app.schemas.item_schema import list_serialize_items
from bson import ObjectId, errors
from app.models.item_model import ItemRead, ItemFromDB
from fastapi import File, UploadFile
from app.config import upload_image
import cloudinary.uploader
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

router = APIRouter()
logger = logging.getLogger(__name__)

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
        for file in files:
            logging.info("Uploading image to cloudinary")
            image_data = await file.read()
            image_url = await upload_image(image_data)
            images.append(image_url)
            logger.info("Image uploaded")
        item_data["images"] = images
        logger.info("Inserting item to mongodb")
        items_collection.insert_one(item_data)
        return {"message": "Item created successfully"}
    except json.JSONDecodeError as e: 
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format") 
    except:
        logger.error("Error creating item") 
        raise HTTPException(status_code=500, detail="Cannot create item")


@router.put("/{item_id}")
async def update_item(item_id: str):
    # TODO: Implement update item
    pass


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    # TODO: Implement delete item
    pass