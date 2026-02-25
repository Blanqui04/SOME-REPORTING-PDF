"""Prometheus metrics for application monitoring.

Exposes key application metrics at ``/metrics`` in Prometheus text
format.  Uses a lightweight implementation without the full
``prometheus_client`` library to keep dependencies minimal.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Metrics storage (in-memory counters/gauges)
# ------------------------------------------------------------------


class _MetricsStore:
    """Thread-safe, in-process metrics store."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def inc(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self._counters[name] = int(self._counters[name]) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        """Record a histogram observation."""
        self._histograms[name].append(value)
        # Keep only last 1000 observations to bound memory
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-500:]

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []

        for name, count in sorted(self._counters.items()):
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {count}")

        for name, gauge_val in sorted(self._gauges.items()):
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {gauge_val}")

        for name, observations in sorted(self._histograms.items()):
            if observations:
                count = len(observations)
                total = sum(observations)
                avg = total / count if count else 0
                lines.append(f"# TYPE {name}_count counter")
                lines.append(f"{name}_count {count}")
                lines.append(f"# TYPE {name}_sum counter")
                lines.append(f"{name}_sum {total:.6f}")
                lines.append(f"# TYPE {name}_avg gauge")
                lines.append(f"{name}_avg {avg:.6f}")

        return "\n".join(lines) + "\n"


# Singleton instance
metrics = _MetricsStore()


# ------------------------------------------------------------------
# Well-known metric names
# ------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = "grafana_reporter_http_requests_total"
HTTP_REQUEST_DURATION = "grafana_reporter_http_request_duration_seconds"
REPORTS_GENERATED_TOTAL = "grafana_reporter_reports_generated_total"
REPORTS_FAILED_TOTAL = "grafana_reporter_reports_failed_total"
PDF_GENERATION_DURATION = "grafana_reporter_pdf_generation_duration_seconds"
PDF_SIZE_BYTES = "grafana_reporter_pdf_size_bytes"
ACTIVE_TASKS = "grafana_reporter_active_celery_tasks"


# ------------------------------------------------------------------
# Helper functions for recording metrics from business logic
# ------------------------------------------------------------------


def record_report_generated() -> None:
    """Increment the generated reports counter."""
    metrics.inc(REPORTS_GENERATED_TOTAL)


def record_report_failed() -> None:
    """Increment the failed reports counter."""
    metrics.inc(REPORTS_FAILED_TOTAL)


def record_pdf_duration(seconds: float) -> None:
    """Record PDF generation duration.

    Args:
        seconds: Time taken to generate the PDF.
    """
    metrics.observe(PDF_GENERATION_DURATION, seconds)


def record_pdf_size(size_bytes: int) -> None:
    """Record generated PDF size.

    Args:
        size_bytes: Size of the PDF in bytes.
    """
    metrics.observe(PDF_SIZE_BYTES, float(size_bytes))


# ------------------------------------------------------------------
# Middleware for HTTP metrics
# ------------------------------------------------------------------


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record HTTP request count and latency metrics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and record metrics.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler.

        Returns:
            HTTP response.
        """
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Skip metrics endpoint itself
        if request.url.path != "/metrics":
            method = request.method
            status_code = response.status_code
            metrics.inc(f"{HTTP_REQUESTS_TOTAL}{{method=\"{method}\",status=\"{status_code}\"}}")
            metrics.observe(HTTP_REQUEST_DURATION, duration)

        return response


# ------------------------------------------------------------------
# Metrics endpoint router
# ------------------------------------------------------------------

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def get_metrics() -> Response:
    """Prometheus-compatible metrics endpoint.

    Returns:
        Plain text response in Prometheus exposition format.
    """
    return Response(
        content=metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
