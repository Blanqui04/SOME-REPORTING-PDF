"""Custom exception classes and FastAPI exception handlers."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(f"{resource} '{identifier}' not found", status_code=404)


class ConflictError(AppError):
    """Raised when a resource already exists (duplicate)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)


class AuthenticationError(AppError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message, status_code=401)


class ReportNotReadyError(AppError):
    """Raised when trying to download a report that is not yet completed."""

    def __init__(self, report_id: str, current_status: str) -> None:
        super().__init__(
            f"Report '{report_id}' is not ready (status: {current_status})",
            status_code=409,
        )


class GrafanaConnectionError(AppError):
    """Raised when Grafana is unreachable."""

    def __init__(self, message: str = "Cannot connect to Grafana") -> None:
        super().__init__(message, status_code=502)


class GrafanaAPIError(AppError):
    """Raised when Grafana returns an unexpected error."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message, status_code=status_code)


class GrafanaNotFoundError(AppError):
    """Raised when a Grafana resource (dashboard/panel) is not found."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(f"Grafana {resource} '{identifier}' not found", status_code=404)


class PDFRenderError(AppError):
    """Raised when PDF generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"PDF rendering failed: {message}", status_code=500)


def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle AppError exceptions and return a JSON response.

    Args:
        request: The incoming HTTP request.
        exc: Exception instance (expected to be AppError).

    Returns:
        JSONResponse with appropriate status code and error detail.
    """
    if not isinstance(exc, AppError):
        logger.error("Unhandled exception in app_error_handler: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    logger.error("AppError [%d]: %s", exc.status_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
