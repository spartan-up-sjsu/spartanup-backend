from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, status
from typing import List, Optional
import json
from bson import ObjectId, errors
from datetime import datetime
from app.config import items_collection, logger
from app.schemas.item_schema import list_serialize_items
from app.models.item_model import ItemCreate, Condition
from app.core.security import get_current_user
from app.services.cloudinary_service import upload_image

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
        logger.info("Inserting item to mongodb")
        items_collection.insert_one(validated_item_dict)
        return {"message": "Item created successfully"}
    except json.JSONDecodeError as e: 
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format") 
    except:
        logger.error("Error creating item") 
        raise HTTPException(status_code=500, detail="Cannot create item")
    
@router.put("/{item_id}")
async def update_item(item_id: str, item: str = Form(...), files: Optional[List[UploadFile]] = File(None)):
    try: 
        logger.info(f"Updating item with ID: {item_id}")
        existing_item = items_collection.find_one({"_id": ObjectId(item_id)})
        if not existing_item:
            logger.error("item not found")
            raise HTTPException(status_code= 404, detail= "Item not found")
        images = existing_item.get("images", [])
        item_data = json.loads(item)
        validated_item = ItemCreate(**item_data)

        if files:
            for file in files:
                logger.info("Uploading new image to cloudinary")
                image_data = await file.read()
                image_url = await upload_image(image_data)
                images.append(image_url)
                logger.info("Image uploaded")
        validated_item_dict = validated_item.model_dump()
        validated_item_dict["images"] = images
        items_collection.update_one(
            {"_id": ObjectId(item_id)}, 
            {"$set": validated_item_dict}
        )
        return {"message": "Item updated successfully"}
    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Cannot update item")

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

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    item: str = Form(...),
    files: List[UploadFile] = File(...),
    sellerId: str = Depends(get_current_user)
):
    try:
        logger.info("Starting item creation process")

        # 1. Parse and validate item data
        item_data = json.loads(item)
        item_data["sellerId"] = sellerId  # Inject authenticated user

        # 2. Upload images to Cloudinary
        images = []
        for file in files:
            logger.info(f"Uploading image: {file.filename}")
            image_data = await file.read()
            image_url = await upload_image(image_data)
            images.append(image_url)

        # 3. Create validated item with timestamps
        validated_item = ItemCreate(
            **item_data,
            images=images,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        # 4. Insert into MongoDB
        result = items_collection.insert_one(validated_item.dict())

        # 5. Return success response
        return {
            "message": "Item created successfully",
            "itemId": str(result.inserted_id)
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON format in item data")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )


