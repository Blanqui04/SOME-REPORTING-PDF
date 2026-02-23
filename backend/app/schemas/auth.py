"""Authentication response schemas."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """JWT token response returned after successful login.

    Attributes:
        access_token: The JWT access token string.
        token_type: Token type, always 'bearer'.
    """

    access_token: str
    token_type: str = "bearer"
