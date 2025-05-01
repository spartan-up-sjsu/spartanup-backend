from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum, auto


class Tags(str, Enum):
    AS_DESCRIBED = "as_described"
    FRIENDLY = "friendly"
    COMMUNICATIVE = "communicative"


class Review(BaseModel):
    item_id: str
    reviewer_id: str
    seller_id: str
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
    tags: Optional[List[Tags]] = None
