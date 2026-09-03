from pydantic import BaseModel, EmailStr

from app.models import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
