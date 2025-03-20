from fastapi import APIRouter, Request, HTTPException, Depends
from app.config import user_collection, report_collection, items_collection
from bson import ObjectId
from app.core.security import verify_access_token

router = APIRouter()

async def checkRole(request: Request):
    token = request.cookies.get("access_token")
    if not token: 
        raise HTTPException(status_code = 401, detail= "Not authenticated")
    
    user_id = verify_access_token(token)
    user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("is_admin" , False):
        raise HTTPException(status_code = 401, detail= "Admins only" )
    else: 
        return True

@router.get("/reported_items")
async def get_reported_items(admin_check: bool = Depends(checkRole)): 
    reported_items = report_collection.find({"status": "pending"})
    reported_items_list = [
        {**post, "_id": str(post["_id"]), "entity_id": str(post["entity_id"]), "reported_by": str(post["reported_by"])}
        for post in reported_items
    ]
    return {"reported_items": reported_items_list}
    
@router.delete("/reported_items")
async def delete_reported_items(entity_id: str, type: str, admin_check: bool = Depends(checkRole)):
    try:
        obj_id = ObjectId(entity_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entity_id format")

    if type == "items":
        deleted_item = items_collection.delete_one({"_id": obj_id})

        if deleted_item.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Post not found")

    report_collection.update_many(
        {"entity_id": obj_id},
        {"$set": {"status": "resolved"}}
    )

    return {"message": "Post deleted and report resolved"}

