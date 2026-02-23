"""Authentication API endpoints."""

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
from backend.app.schemas.auth import TokenResponse
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

    Args:
        form_data: OAuth2 form with username and password fields.
        db: Database session.
        settings: Application settings for JWT configuration.

    Returns:
        JWT access token response.
    """
    service = AuthService(db)
    user = service.authenticate_user(form_data.username, form_data.password)

    access_token = create_access_token(
        subject=str(user.id),
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(access_token=access_token)


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
