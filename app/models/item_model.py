from typing import Optional, List, Literal
from pydantic import BaseModel, HttpUrl, validator
from datetime import datetime


class ItemCreate(BaseModel):
    title: str
    description: Optional[str]
    images: List[str]
    price: float
    condition: str
    category: str
    sellerId: str
    status: Optional[str] = "active"
    location: Optional[str]


class ItemRead(ItemCreate):
    createdAt: datetime = None
    updatedAt: datetime = None


class ItemFromDB(ItemRead):
    _id: str

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    condition: Optional[Literal["New", "Like New", "Used", "Poor"]] = None
    description: Optional[str] = None
    images: Optional[List[HttpUrl]] = None

    @validator("images", each_item=True)
    def validate_cloudinary_url(cls, v):
        if not str(v).startswith("https://res.cloudinary.com/"):
            raise ValueError("Only Cloudinary image URLs are allowed")
        return v
    @validator("price")
    def validate_price(cls, price: float):
        if price < 0:
            raise ValueError("Price must be a positive number")
        return price