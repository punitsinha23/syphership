from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime

class Usercreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class PublicUser(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
    id: int
    username: str
    email: str
    created_at: datetime

class RefreshToken(BaseModel):
    refresh_token: str
