from pydantic import BaseModel, Field
from typing import Optional


class Review(BaseModel):
    item_id: str
    reviewer_id: str
    seller_id: str
    rating: int = Field(..., ge=1, le=5) 
    comment: Optional[str] = None