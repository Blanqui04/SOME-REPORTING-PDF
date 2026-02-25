"""Authentication response schemas."""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """JWT token response schema.

    Attributes:
        access_token: The JWT access token string.
        token_type: The token type (always 'bearer').
        requires_totp: Whether TOTP verification is required before access.
    """

    access_token: str
    token_type: str = "bearer"
    requires_totp: bool = False


class TOTPSetupResponse(BaseModel):
    """Response for TOTP setup initiation.

    Attributes:
        secret: The TOTP secret (base32).
        qr_code_base64: QR code image as base64 PNG.
        provisioning_uri: The otpauth:// URI.
    """

    secret: str
    qr_code_base64: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    """Request to verify a TOTP token.

    Attributes:
        token: The 6-digit TOTP token.
    """

    token: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TOTPEnableRequest(BaseModel):
    """Request to enable TOTP after verifying the initial token.

    Attributes:
        secret: The TOTP secret from setup.
        token: The 6-digit verification token.
    """

    secret: str = Field(..., min_length=16, max_length=64)
    token: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
