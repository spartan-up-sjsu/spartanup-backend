from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import Literal

class Report(BaseModel):
    entity_id: str
    reason: str
    type: Literal["user", "product"]
    details: str 
    reported_at: datetime = Field(default_factory=datetime.utcnow) 
    status: Literal["pending", "resolved", "dismissed", "escalated"] = Field(default="pending")