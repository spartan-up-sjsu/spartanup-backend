from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime

def serialize_item(item) -> dict:
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
        "createdAt": item["createdAt"].isoformat() if item["createdAt"] else None, 
        "updatedAt": item["updatedAt"].isoformat() if item["updatedAt"] else None 
    }

def list_serialize_items(items) -> list:
    return [serialize_item(item) for item in items]