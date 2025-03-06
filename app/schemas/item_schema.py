from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from app.models.item_model import ItemFromDB


def serialize_item(item: ItemFromDB) -> dict:
    return {
        "_id": str(item["_id"]),
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "images": [str(url) for url in item.get("images", [])],
        "price": item["price"],
        "condition": item["condition"],
        "category": item["category"],
        "seller_id": str(item["seller_id"]),
        "status": item.get("status", "active"),
        "location": item.get("location", ""),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at")
    }


def list_serialize_items(items) -> list:
    return [serialize_item(item) for item in items]
