from pydantic import BaseModel
from bson import ObjectId as _ObjectId
from typing import Literal
from datetime import datetime
from typing_extensions import Annotated
from pydantic.functional_validators import AfterValidator

def check_object_id(value: str) -> str:
    if not _ObjectId.is_valid(value):
        raise ValueError('Invalid ObjectId')
    return value

ObjectId = Annotated[str, AfterValidator(check_object_id)]

class ChatRequest(BaseModel):
    item_id: str
    buyer_id: str
    seller_id: str

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