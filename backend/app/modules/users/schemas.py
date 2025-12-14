from pydantic import BaseModel, EmailStr
from typing import Optional

# Schema dasar
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"

# Schema buat Create User (User input password di sini)
class UserCreate(UserBase):
    password: str
    system_username: Optional[str] = None

# Schema buat Response (Password dihilangkan biar aman)
class UserResponse(UserBase):
    id: int
    system_username: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True