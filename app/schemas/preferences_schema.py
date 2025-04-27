from pydantic import BaseModel
from typing import Optional

class PreferencesRead(BaseModel):
    profile_visibility: str
    push_notifications: bool
    email_notifications: bool
    campus_trading_mode: bool
    dark_mode: bool
    phone_number: Optional[str] = None

class PreferencesUpdate(BaseModel):
    profile_visibility: Optional[str] = None
    push_notifications: Optional[bool] = None
    email_notifications: Optional[bool] = None
    campus_trading_mode: Optional[bool] = None
    dark_mode: Optional[bool] = None
    phone_number: Optional[str] = None