from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from enum import Enum
import re

class Condition(str, Enum):
    NEW = "New"
    LIKE_NEW = "Like New"
    USED = "Used"
    POOR = "Poor"


class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    images: List[str]
    price: float
    condition: Condition
    category: str
    sellerId: str
    status: Optional[str] = "active"
    location: Optional[str] = None

    @validator('images')
    def validate_cloudinary_urls(cls, v):
        cloudinary_regex = r'^https?://res\.cloudinary\.com/[^/]+/image/upload/.*'
        for url in v:
            if not re.match (cloudinary_regex, str(url)):
                raise ValueError('Only Cloudinary urls are allowed')
        return v


class ItemRead(ItemCreate):
    createdAt: datetime = None
    updatedAt: datetime = None


class ItemFromDB(ItemRead):
    id: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
