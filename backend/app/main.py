"""FastAPI application factory and entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import Settings
from backend.app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _get_settings() -> Settings:
    """Load settings without circular import from deps."""
    from backend.app.api.deps import get_settings

    return get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown events."""
    settings = _get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Initialize shared GrafanaClient singleton
    from backend.app.services.grafana_client import GrafanaClient

    grafana_client = GrafanaClient(
        base_url=settings.GRAFANA_URL,
        api_key=settings.GRAFANA_API_KEY,
        timeout=settings.GRAFANA_TIMEOUT,
    )
    app.state.grafana_client = grafana_client

    yield

    # Cleanup: close shared GrafanaClient
    grafana_client.close()
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with middleware, routers,
        and exception handlers.
    """
    settings = _get_settings()

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    from backend.app.core.middleware import RequestIDMiddleware

    application.add_middleware(RequestIDMiddleware)

    # Exception handlers
    from backend.app.core.exceptions import AppError, app_error_handler

    application.add_exception_handler(AppError, app_error_handler)

    # API routers
    from backend.app.api.v1.router import v1_router

    application.include_router(v1_router)

    @application.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return application


app = create_app()
