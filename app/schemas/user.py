"""
User Pydantic Schemas.

Defines request validation and response models for user registration,
login, and profile retrieval, ensuring sensitive data (password_hash) is never exposed.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserRegister(BaseModel):
    """
    Schema for user registration requests.
    Enforces name length, valid email syntax, password strength, and allowed roles.
    """
    name: str = Field(..., min_length=2, max_length=100, examples=["Jane Doe"])
    email: EmailStr = Field(..., examples=["jane.doe@relief.org"])
    password: str = Field(..., min_length=6, max_length=100, examples=["StrongPassword123!"])
    role: UserRole = Field(default=UserRole.VOLUNTEER, examples=[UserRole.VOLUNTEER])


class UserLogin(BaseModel):
    """
    Schema for standard JSON login requests.
    """
    email: EmailStr = Field(..., examples=["jane.doe@relief.org"])
    password: str = Field(..., examples=["StrongPassword123!"])


class UserResponse(BaseModel):
    """
    Safe public user representation returned by API endpoints.
    Notice that 'password_hash' is intentionally excluded.
    """
    id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime

    # Enables Pydantic to read attributes directly from SQLAlchemy ORM models
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Schema returned upon successful authentication.
    Complies with OAuth2 Bearer token specifications.
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Internal schema representing the verified claims inside a JWT.
    """
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
