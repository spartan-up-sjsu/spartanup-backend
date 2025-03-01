from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from bson import ObjectId as _ObjectId
from typing_extensions import Annotated
from pydantic.functional_validators import AfterValidator

def check_object_id(value: str) -> str:
    if not _ObjectId.is_valid(value):
        raise ValueError('Invalid ObjectId')
    return value

ObjectId = Annotated[str, AfterValidator(check_object_id)]


class ItemCreate(BaseModel):
    title: str
    description: Optional[str]
    images: List[str]
    price: float
    condition: str
    category: str
    sellerId: ObjectId
    status: Optional[str] = "active"
    location: Optional[str]


class ItemRead(ItemCreate):
    createdAt: datetime = None
    updatedAt: datetime = None


class ItemFromDB(ItemRead):
    _id: str

class Config:
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str} 