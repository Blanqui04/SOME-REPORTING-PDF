"""FastAPI dependency injection functions."""

import uuid
from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import get_session_factory
from backend.app.core.security import decode_access_token
from backend.app.models.user import User
from backend.app.services.grafana_client import GrafanaClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Returns:
        Application Settings instance.
    """
    return Settings()  # type: ignore[call-arg]


def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed after use.

    Args:
        settings: Application settings (injected).

    Yields:
        Active database session.
    """
    session_factory = get_session_factory(settings)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Decode JWT token and return the authenticated user.

    Args:
        token: JWT access token from Authorization header.
        db: Database session.
        settings: Application settings for JWT configuration.

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException 401: If token is invalid or user not found/inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id_str = decode_access_token(
            token=token,
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        raise credentials_exception from e

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    return user


def get_grafana_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GrafanaClient:
    """Return the shared GrafanaClient singleton from app state.

    Falls back to creating a new instance if app state is not available
    (e.g. during testing).

    Args:
        settings: Application settings with Grafana configuration.

    Returns:
        GrafanaClient instance connected to the configured Grafana URL.
    """
    from backend.app.main import app

    client: GrafanaClient | None = getattr(app.state, "grafana_client", None)
    if client is not None:
        return client

    return GrafanaClient(
        base_url=settings.GRAFANA_URL,
        api_key=settings.GRAFANA_API_KEY,
        timeout=settings.GRAFANA_TIMEOUT,
    )
