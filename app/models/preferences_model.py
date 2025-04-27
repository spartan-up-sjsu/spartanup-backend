from typing import Optional
from pydantic import BaseModel

class PreferencesUpdate(BaseModel):
    push_notifications: Optional[bool] = None
    email_notifications: Optional[bool] = None
    campus_trading_mode: Optional[bool] = None
    dark_mode: Optional[bool] = None
    profile_visibility: Optional[str] = None  # e.g., 'SJSU Students Only', 'Everyone', etc.
