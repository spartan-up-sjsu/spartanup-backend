from fastapi import APIRouter, Depends, HTTPException, Form, Request, File, UploadFile, Body
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

# Removed the PATCH /product/{item_id} endpoint. Item updates are now handled in app/routers/items.py for consistency.
