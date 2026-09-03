import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import Language, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: Role
    phone: str | None = Field(default=None, max_length=32)
    preferred_language: Language = Language.EN


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    phone: str | None
    role: Role
    preferred_language: Language
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None
    created_at: datetime


class UserUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    preferred_language: Language | None = None


class DeactivationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
