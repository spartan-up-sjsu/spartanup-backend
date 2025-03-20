from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from typing import Optional

class Report(BaseModel):
    entity_id: str
    reported_by: str
    reason: str
    reported_at: datetime = Field(default_factory=datetime.utcnow) 
    status: Optional[str] = "pending"