"""SQLAlchemy engine and session configuration."""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine(database_url: str) -> object:
    """Create or return the cached SQLAlchemy engine.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        logger.info("Database engine created")
    return _engine


def get_session_factory(settings: Settings) -> sessionmaker[Session]:
    """Return a sessionmaker bound to the application engine.

    Args:
        settings: Application settings containing database_url.

    Returns:
        Configured sessionmaker instance.
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = _get_engine(settings.database_url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db(settings: Settings | None = None) -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed after use.

    This is used as a FastAPI dependency. The settings parameter
    is injected via the deps module.

    Args:
        settings: Application settings (injected by FastAPI DI).

    Yields:
        Active database session.
    """
    from backend.app.api.deps import get_settings

    if settings is None:
        settings = get_settings()

    session_factory = get_session_factory(settings)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
