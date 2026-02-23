"""User request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration requests.

    Attributes:
        email: Valid email address.
        username: Alphanumeric username (3-100 chars).
        password: User password (8-128 chars).
    """

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Schema for user responses (password excluded).

    Attributes:
        id: User UUID.
        email: User email address.
        username: User display name.
        is_active: Whether the user account is active.
        created_at: Account creation timestamp.
    """

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
