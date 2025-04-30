from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from app.config import user_collection, upload_image, preferences_collection
from app.routers.api import get_current_user_id_id
from app.schemas.preferences_schema import PreferencesUpdate, PreferencesRead
from app.config import logger
from bson import ObjectId

router = APIRouter()


@router.get("/", response_model=PreferencesRead)
async def get_preferences(user_id: str = Depends(get_current_user_id_id)):
    preferences = preferences_collection.find_one({"user_id": ObjectId(user_id)})
    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")
    logger.info(preferences)
    return PreferencesRead(**preferences['preferences'])


@router.patch("/", response_model=PreferencesRead)
async def update_preferences(
    update: PreferencesUpdate, user_id: str = Depends(get_current_user_id_id)
):
    preferences = preferences_collection.find_one({"user_id": ObjectId(user_id)})
    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")
        
    # Only include fields that were explicitly set in the request
    update_data = update.model_dump(exclude_unset=True)
    
    # Update only the fields that were provided in the request
    for key, value in update_data.items():
        if key in preferences['preferences']:
            preferences['preferences'][key] = value
            logger.info("Updated preference: %s", key)
    
    preferences_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": {"preferences": preferences['preferences']}},
    )
    
    # Fetch the updated document
    updated_preferences = preferences_collection.find_one({"user_id": ObjectId(user_id)})
    return PreferencesRead(**updated_preferences['preferences'])


@router.patch("/image")
async def update_image(
    image: UploadFile = File(...), user_id: str = Depends(get_current_user_id_id)
):
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Read image bytes
    image_bytes = await image.read()
    # Upload to Cloudinary
    image_url = await upload_image(image_bytes)
    # Update user profile picture
    user_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"picture": image_url}}
    )
    return {"picture": image_url}
