from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId as _ObjectId
from typing_extensions import Annotated
from pydantic.functional_validators import AfterValidator

def check_object_id(value: str) -> str:
    if not _ObjectId.is_valid(value):
        raise ValueError('Invalid ObjectId')
    return value

ObjectId = Annotated[str, AfterValidator(check_object_id)]


class Message(BaseModel):
    id: ObjectId 
    content: str  
    sent_by: ObjectId
    conversation_id: ObjectId 
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
