from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
