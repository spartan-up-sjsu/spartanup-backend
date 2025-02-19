from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from app.models.item_model import ItemFromDB


def serialize_item(item: ItemFromDB) -> dict:
    return {
        "_id": str(item["_id"]),
        "title": item["title"],
        "description": item.get("description", ""),
        "images": [str(url) for url in item.get("images", [])],
        "price": item["price"],
        "condition": item["condition"],
        "category": item["category"],
        "sellerId": str(item["sellerId"]),
        "status": item.get("status", "active"),
        "location": item.get("location", ""),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt")
    }


def list_serialize_items(items) -> list:
    return [serialize_item(item) for item in items]
