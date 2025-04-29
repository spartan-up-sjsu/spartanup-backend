from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from app.config import user_collection, upload_image
from app.routers.api import get_current_user_id
from app.schemas.preferences_schema import PreferencesUpdate, PreferencesRead
from bson import ObjectId

router = APIRouter()


@router.get("/", response_model=PreferencesRead)
async def get_preferences(user_id: str = Depends(get_current_user_id)):
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    preferences = user.get("preferences", {})
    return PreferencesRead(**preferences)


@router.patch("/", response_model=PreferencesRead)
async def update_preferences(
    update: PreferencesUpdate, user_id: str = Depends(get_current_user_id)
):
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="No preferences provided for update"
        )
    user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {f"preferences.{k}": v for k, v in update_data.items()}},
    )
    updated_user = user_collection.find_one({"_id": ObjectId(user_id)})
    preferences = updated_user.get("preferences", {})
    return PreferencesRead(**preferences)


@router.patch("/image")
async def update_image(
    image: UploadFile = File(...), user_id: str = Depends(get_current_user_id)
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
