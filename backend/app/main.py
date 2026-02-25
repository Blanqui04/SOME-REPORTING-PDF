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
        description=(
            "REST API for automated PDF report generation from Grafana dashboards. "
            "Supports scheduled generation, multi-language output, custom templates, "
            "and integrations with Slack/Teams webhooks and S3/MinIO storage."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "auth", "description": "Authentication: login, register, TOTP 2FA"},
            {"name": "reports", "description": "PDF report generation, listing, and download"},
            {"name": "grafana", "description": "Grafana dashboard and panel discovery"},
            {"name": "schedules", "description": "Scheduled report generation (cron-based)"},
            {"name": "templates", "description": "PDF template management and branding"},
            {"name": "audit", "description": "Audit log for admin users"},
            {"name": "i18n", "description": "Internationalization and translations"},
            {"name": "health", "description": "Health check and readiness probe"},
            {"name": "metrics", "description": "Prometheus-compatible application metrics"},
        ],
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        contact={
            "name": "Grafana PDF Reporter",
            "url": "https://github.com/grafana-pdf-reporter",
        },
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

    # Rate limiting
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    from backend.app.core.rate_limit import limiter

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Exception handlers
    from backend.app.core.exceptions import AppError, app_error_handler

    application.add_exception_handler(AppError, app_error_handler)

    # Prometheus metrics (optional)
    if settings.PROMETHEUS_ENABLED:
        from backend.app.core.metrics import PrometheusMiddleware
        from backend.app.core.metrics import router as metrics_router

        application.add_middleware(PrometheusMiddleware)
        application.include_router(metrics_router)

    # API routers
    from backend.app.api.v1.router import v1_router

    application.include_router(v1_router)

    @application.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return application


app = create_app()
