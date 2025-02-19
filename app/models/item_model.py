from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime


class ItemRead(BaseModel):
    title: str
    description: Optional[str]
    images: List[str]
    price: float
    condition: str
    category: str
    sellerId: str
    status: Optional[str] = "active"
    location: Optional[str]
    createdAt: datetime = None
    updatedAt: datetime = None


class ItemFromDB(ItemRead):
    _id: str
