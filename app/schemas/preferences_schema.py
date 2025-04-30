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
    profile_visibility: Optional[str] = "public"
    push_notifications: Optional[bool] = True
    email_notifications: Optional[bool] = True
    campus_trading_mode: Optional[bool] = True
    dark_mode: Optional[bool] = False
    phone_number: Optional[str] = None