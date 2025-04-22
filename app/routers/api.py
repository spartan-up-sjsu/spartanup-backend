from fastapi import APIRouter, Depends, HTTPException, Form, Request, File, UploadFile
from typing import List
from app.config import items_collection, user_collection
from app.core.security import verify_access_token
from app.config import logger, upload_image
from bson import ObjectId
from typing import Optional
import json 
from app.models.item_model import ItemRead, ItemFromDB, ItemCreate, ProductUpdate

router = APIRouter()

from fastapi import HTTPException, Request

async def get_current_user_id(request: Request):
   #Getting from authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token_type, token = auth_header.split(" ") if " " in auth_header else (None, None)
        if token_type.lower() == "bearer" and token:
            user_id = verify_access_token(token)
            return user_id
    
    #Getting from the cookies
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_access_token(token)
    return user_id

@router.patch("/product/{item_id}")
async def update_item(item_id: str, update: ProductUpdate, user_id: dict = Depends(get_current_user_id)):
    try: 
        logger.info(f"Updating item with ID: {item_id}")
        existing_item = items_collection.find_one({"_id": ObjectId(item_id)})
        if not existing_item:
            logger.error("item not found")
            raise HTTPException(status_code= 404, detail= "Item not found")
    
        if str(existing_item["seller_id"]) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    
        update_data = update.model_dump(exclude_unset=True) 
        if "images" in update_data:
            update_data["images"] = [str(url) for url in update_data["images"]]

        items_collection.update_one(
            {"_id": ObjectId(item_id)}, 
            {"$set": update_data}
        )
        return {"message": "Item updated successfully"}
    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Cannot update item")
