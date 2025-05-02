from typing import Optional, List, Literal
from pydantic import BaseModel, HttpUrl, Field, validator
from datetime import datetime
from bson import ObjectId as _ObjectId
from typing_extensions import Annotated
from pydantic.functional_validators import AfterValidator


def check_object_id(value: str) -> str:
    if not _ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return value


ObjectId = Annotated[str, AfterValidator(check_object_id)]


class ItemCreate(BaseModel):
    title: str
    description: Optional[str]
    price: float
    condition: str
    category: str
    status: Optional[str] = "active"
    createdAt: datetime = Field(default_factory=datetime.utcnow)


class ItemRead(ItemCreate):
    created_at: datetime = None
    updated_at: datetime = None


class ItemFromDB(ItemRead):
    _id: str


class Config:
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    condition: Optional[Literal["New", "Like New", "Used", "Poor"]] = None
    description: Optional[str] = None
    status: Optional[Literal["active", "sold"]] = None
    images: Optional[List[HttpUrl]] = None
    remove_urls: Optional[List[str]] = None

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
