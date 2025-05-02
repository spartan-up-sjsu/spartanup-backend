from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form,
    Request,
    File,
    UploadFile,
    Body,
)
from typing import List, Optional
from app.config import items_collection, user_collection, conversations_collection
from app.schemas.item_schema import list_serialize_items
from bson import ObjectId, errors
from app.models.item_model import ItemRead, ItemFromDB, ItemCreate, ProductUpdate
from app.config import upload_image
from app.config import logger
import cloudinary.uploader
import json
from typing import Optional
from app.core.security import verify_access_token
from app.routers.api import get_current_user_id
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/")
async def get_items(
    user_id: str = Depends(get_current_user_id),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    personal_only: Optional[bool] = False,
    seller_id: Optional[str] = None,
    recency: Optional[int] = None,  # Number of days, e.g. 7, 30, 90
):
    try:
        logger.info(
            f"[GET /items] Retrieving items | user_id={user_id}, category={category}, min_price={min_price}, max_price={max_price}, search={search}, personal_only={personal_only}, recency={recency}"
        )
        if personal_only:
            query = {"seller_id": user_id}
            logger.debug(f"Filtering for personal items only. Query: {query}")
        else:
            query = {"seller_id": {"$ne": user_id}}
            logger.debug(f"Filtering for non-personal items. Query: {query}")
        if category:
            query["category"] = category
            logger.debug(f"Added category filter: {category}")
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            query["price"] = price_filter
            logger.debug(f"Added price filter: {price_filter}")
        if search:
            search_pattern = search.lower()
            query["$or"] = [
                {
                    "$expr": {
                        "$regexMatch": {
                            "input": {"$toLower": "$title"},
                            "regex": search_pattern,
                        }
                    }
                },
                {
                    "$expr": {
                        "$regexMatch": {
                            "input": {"$toLower": "$description"},
                            "regex": search_pattern,
                        }
                    }
                },
                {"status": "active"},
            ]
            logger.debug(f"Added search filter for pattern: {search_pattern}")
        if seller_id:
            query["seller_id"] = seller_id
            logger.debug(f"Added seller_id filter: {seller_id}")
        if recency is not None:
            try:
                days = int(recency)
                since_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)
                query["createdAt"] = {"$gte": since_date}
                logger.info(
                    f"Filtering items created in the last {days} days (since {since_date})"
                )
            except Exception as e:
                logger.warning(f"Invalid recency value: {recency} | Error: {str(e)}")
        logger.debug(f"Final MongoDB query: {query}")
        items_cursor = items_collection.find(query).sort("createdAt", -1)
        items = list_serialize_items(items_cursor)
        logger.debug(f"Items found: {len(items)}")
        return {"message": "Items retrieved successfully", "data": items}
    except Exception as e:
        logger.error(f"Unable to retrieve items: {str(e)}")
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
        item["_id"] = str(item["_id"])
        item["seller_id"] = str(item["seller_id"])
        return {"message": "Item retrieved successfully", "data": item}
    except errors.InvalidId:
        logger.error(f"Invalid ObjectId format: {item_id}")
        raise HTTPException(status_code=400, detail="Invalid item ID format")
    except Exception as e:
        logger.error(f"Unexpected error retrieving item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/")
async def create_item(
    item: str = Form(...),
    files: List[UploadFile] = File(...),
    user_id=Depends(get_current_user_id),
):
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
        validated_item_dict["seller_id"] = user_id
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


@router.patch("/{item_id}")
async def update_item(
    item_id: str,
    update: str = Form(...),
    user_id: str = Depends(get_current_user_id),
    add_files: Optional[List[UploadFile]] = File(None),
):
    try:
        logger.info(
            f"[PATCH /items/{{item_id}}] Request to update item: {item_id} by user: {user_id}"
        )
        logger.debug(f"Raw update payload: {update}")
        logger.debug(f"add_files: {add_files}")
        existing_item = items_collection.find_one({"_id": ObjectId(item_id)})
        if not existing_item:
            logger.error(f"Item {item_id} not found in database.")
            raise HTTPException(status_code=404, detail="Item not found")
        logger.info(f"Item found: {existing_item}")
        if str(existing_item["seller_id"]) != str(user_id):
            logger.warning(
                f"User {user_id} not authorized to edit item {item_id} (seller: {existing_item['seller_id']})"
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to edit this product"
            )
        try:
            update_data_dict = json.loads(update)
            logger.info(f"Parsed update data: {update_data_dict}")
            update_data = ProductUpdate(**update_data_dict).model_dump(
                exclude_unset=True
            )
            logger.info(f"Validated update data: {update_data}")
        except Exception as e:
            logger.error(f"Invalid update format: {str(e)} | Raw: {update}")
            raise HTTPException(status_code=400, detail="Invalid update format")
        images = existing_item.get("images", [])
        logger.debug(f"Current images: {images}")
        # Remove specified URLs if present in update_data
        remove_urls = update_data.pop("remove_urls", None)
        if remove_urls:
            logger.info(f"Removing images: {remove_urls}")
            images = [img for img in images if img not in remove_urls]
            logger.debug(f"Images after removal: {images}")
        # Add new files
        if add_files:
            for file in add_files:
                logger.info(f"Uploading new image to cloudinary: {file.filename}")
                image_data = await file.read()
                image_url = await upload_image(image_data)
                logger.info(f"Uploaded image URL: {image_url}")
                images.append(image_url)
            logger.debug(f"Images after addition: {images}")
        update_data["images"] = images
        logger.info(f"Final update_data to be set: {update_data}")
        result = items_collection.update_one(
            {"_id": ObjectId(item_id)}, {"$set": update_data}
        )
        logger.info(
            f"MongoDB update result: matched={result.matched_count}, modified={result.modified_count}"
        )
        return {"message": "Item updated successfully"}
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in update payload")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Cannot update item")


# Example response: {"message":"Inquiries retrieved successfully","data":[{"status":"inprogress","created_at":"2025-05-01T02:06:31.530000","updated_at":"2025-05-01T02:06:31.530000","conversation_id":"6812d76b37f58f25ff60b6ae","buyer":{"_id":"6812bf5ddc3637053b41f4c7","email":"thedrun2004@gmail.com","profile_picture":null,"rating":null}}]}
@router.get("/{item_id}/inquiries")
async def get_item_inquiries(
    item_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get users who have inquired about a specific item.

    This endpoint uses MongoDB's aggregation pipeline to fetch users who have
    started conversations about the item, including their profile information.
    """
    try:
        logger.info(
            f"[GET /items/{item_id}/inquiries] Retrieving inquiries for item: {item_id}"
        )

        # First, verify the item exists and the requester is the seller
        item = items_collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            logger.error(f"Item {item_id} not found")
            raise HTTPException(status_code=404, detail="Item not found")

        if str(item["seller_id"]) != str(user_id):
            logger.warning(
                f"User {user_id} not authorized to view inquiries for item {item_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Only the seller can view inquiries for this item",
            )

        # Use aggregation pipeline to get users who inquired about the item
        pipeline = [
            # Match conversations for this item
            {"$match": {"item_id": ObjectId(item_id)}},
            # Lookup user information for each buyer
            {
                "$lookup": {
                    "from": "users",
                    "localField": "buyer_id",
                    "foreignField": "_id",
                    "as": "buyer_info",
                }
            },
            # Unwind the buyer_info array
            {"$unwind": "$buyer_info"},
            # Project only the fields we need
            {
                "$project": {
                    "_id": 0,
                    "conversation_id": "$_id",
                    "status": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "buyer": {
                        "_id": "$buyer_info._id",
                        "full_name": {
                            "$ifNull": ["$buyer_info.full_name", "$buyer_info.name"]
                        },
                        "email": "$buyer_info.email",
                        "picture": {"$ifNull": ["$buyer_info.picture", None]},
                        "rating": {"$ifNull": ["$buyer_info.rating", None]},
                    },
                }
            },
            # Sort by most recent first
            {"$sort": {"updated_at": -1}},
        ]

        inquiries = list(conversations_collection.aggregate(pipeline))

        # Convert ObjectId to string for JSON serialization
        for inquiry in inquiries:
            inquiry["conversation_id"] = str(inquiry["conversation_id"])
            inquiry["buyer"]["_id"] = str(inquiry["buyer"]["_id"])

        logger.info(f"Found {len(inquiries)} inquiries for item {item_id}")
        return {"message": "Inquiries retrieved successfully", "data": inquiries}

    except errors.InvalidId:
        logger.error(f"Invalid ObjectId format: {item_id}")
        raise HTTPException(status_code=400, detail="Invalid item ID format")
    except Exception as e:
        logger.error(f"Error retrieving inquiries for item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Cannot retrieve inquiries")
