from pydantic import BaseModel
from bson import ObjectId
from typing import Literal
from datetime import datetime

class Conversation(BaseModel):
    id: ObjectId
    item_id: ObjectId
    seller_id: ObjectId
    buyer_id: ObjectId
    status: Literal["inprogress", "completed"] = "inprogress"
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

class Config:
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}