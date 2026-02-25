"""Rate limiting configuration using slowapi.

Provides a shared limiter instance and key functions for
per-IP and per-user rate limiting.
"""

import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _get_rate_limit_key(request: Request) -> str:
    """Build a rate limit key from the client IP or authenticated user.

    Uses the user ID if available (from auth middleware), otherwise
    falls back to the remote IP address.

    Args:
        request: FastAPI request object.

    Returns:
        String key for rate limiting.
    """
    # If user is authenticated, use user ID for rate limiting
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"
    return get_remote_address(request)


# Global limiter instance with sensible defaults
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=["200/minute"],
    storage_uri="memory://",  # Use Redis in production via settings
)
