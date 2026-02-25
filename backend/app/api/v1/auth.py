"""Authentication API endpoints.

Supports local and LDAP login, TOTP 2FA setup/verification.
"""

import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, get_settings
from backend.app.core.config import Settings
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.schemas.auth import (
    TokenResponse,
    TOTPEnableRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
)
from backend.app.schemas.user import UserCreate, UserResponse
from backend.app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Register a new user account.

    Args:
        user_data: User registration data (email, username, password).
        db: Database session.

    Returns:
        The newly created user profile.
    """
    service = AuthService(db)
    user = service.register_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Authenticate user and return a JWT access token.

    If LDAP is enabled, tries LDAP first, then falls back to local auth.
    If the user has TOTP enabled, the response includes requires_totp=True
    and a short-lived token that must be verified via /auth/totp/verify.

    Args:
        form_data: OAuth2 form with username and password fields.
        db: Database session.
        settings: Application settings for JWT configuration.

    Returns:
        JWT access token response.
    """
    service = AuthService(db, settings)
    user = None

    # Try LDAP first if enabled
    if settings.LDAP_ENABLED:
        try:
            user = service.authenticate_ldap(form_data.username, form_data.password)
        except Exception:  # noqa: BLE001
            logger.debug("LDAP auth failed, falling back to local auth")

    # Fall back to local auth
    if user is None:
        user = service.authenticate_user(form_data.username, form_data.password)

    # Check if TOTP is required
    requires_totp = bool(user.totp_enabled and user.totp_secret)
    expire_minutes = 5 if requires_totp else settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(minutes=expire_minutes),
    )

    return TokenResponse(
        access_token=access_token,
        requires_totp=requires_totp,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the currently authenticated user's profile.

    Args:
        current_user: The authenticated user (injected via JWT).

    Returns:
        Current user profile data.
    """
    return UserResponse.model_validate(current_user)


# --- TOTP 2FA Endpoints ---


@router.post("/totp/setup", response_model=TOTPSetupResponse)
def totp_setup(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TOTPSetupResponse:
    """Generate a new TOTP secret and QR code for the user.

    Args:
        current_user: The authenticated user.
        db: Database session.
        settings: Application settings.

    Returns:
        TOTP secret, QR code (base64), and provisioning URI.
    """
    service = AuthService(db, settings)
    secret, qr_base64, uri = service.setup_totp(current_user.id)

    return TOTPSetupResponse(
        secret=secret,
        qr_code_base64=qr_base64,
        provisioning_uri=uri,
    )


@router.post(
    "/totp/enable",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def totp_enable(
    request: TOTPEnableRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    """Enable TOTP 2FA after verifying the initial token.

    Args:
        request: Secret and verification token.
        current_user: The authenticated user.
        db: Database session.
        settings: Application settings.

    Returns:
        Updated user profile with totp_enabled=True.
    """
    service = AuthService(db, settings)
    service.enable_totp(current_user.id, request.secret, request.token)

    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/totp/disable", response_model=UserResponse)
def totp_disable(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    """Disable TOTP 2FA for the current user.

    Args:
        current_user: The authenticated user.
        db: Database session.
        settings: Application settings.

    Returns:
        Updated user profile with totp_enabled=False.
    """
    service = AuthService(db, settings)
    service.disable_totp(current_user.id)

    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/totp/verify", response_model=TokenResponse)
def totp_verify(
    request: TOTPVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Verify TOTP token and issue a full-access JWT.

    Called after login when requires_totp=True. The short-lived token
    from login is used to authenticate, then a full-duration token is
    issued after successful TOTP verification.

    Args:
        request: The 6-digit TOTP token.
        current_user: The authenticated user (via short-lived token).
        db: Database session.
        settings: Application settings.

    Returns:
        Full-duration JWT access token.
    """
    service = AuthService(db, settings)
    service.verify_totp(current_user.id, request.token)

    access_token = create_access_token(
        subject=str(current_user.id),
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(access_token=access_token, requires_totp=False)
