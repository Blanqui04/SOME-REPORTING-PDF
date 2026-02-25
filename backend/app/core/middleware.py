"""Request ID middleware for log traceability."""

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject a unique X-Request-ID header into every request/response.

    This allows correlating log entries across a single request lifecycle.
    If the client sends an X-Request-ID header, it is preserved; otherwise
    a new UUID4 is generated.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request and inject request ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/endpoint in the chain.

        Returns:
            HTTP response with X-Request-ID header.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store on request state for use in handlers/services
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
