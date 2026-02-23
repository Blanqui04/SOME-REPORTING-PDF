"""Grafana HTTP API client wrapper."""

import logging

import httpx

from backend.app.core.exceptions import (
    GrafanaAPIError,
    GrafanaConnectionError,
    GrafanaNotFoundError,
)

logger = logging.getLogger(__name__)


class GrafanaClient:
    """HTTP client wrapper for the Grafana API.

    Encapsulates all communication with Grafana, providing typed
    methods for dashboard listing, detail retrieval, and panel rendering.

    Args:
        base_url: Grafana root URL (e.g. 'http://grafana:3000').
        api_key: Grafana Service Account API key.
        timeout: Request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def list_dashboards(self, search: str | None = None) -> list[dict]:
        """List dashboards from Grafana Search API.

        Calls GET /api/search?type=dash-db&query={search}

        Args:
            search: Optional search query string.

        Returns:
            List of dashboard summary dicts with uid, title, url, tags.

        Raises:
            GrafanaConnectionError: If Grafana is unreachable.
            GrafanaAPIError: If Grafana returns an error status.
        """
        params: dict[str, str] = {"type": "dash-db"}
        if search:
            params["query"] = search

        response = self._request("GET", "/api/search", params=params)
        return response.json()

    def get_dashboard(self, uid: str) -> dict:
        """Get full dashboard details by UID.

        Calls GET /api/dashboards/uid/{uid}

        Args:
            uid: The Grafana dashboard UID.

        Returns:
            Dashboard detail dict including panels and metadata.

        Raises:
            GrafanaNotFoundError: If dashboard UID does not exist.
            GrafanaConnectionError: If Grafana is unreachable.
        """
        response = self._request("GET", f"/api/dashboards/uid/{uid}")
        return response.json()

    def render_panel(
        self,
        dashboard_uid: str,
        panel_id: int,
        width: int = 1000,
        height: int = 500,
        from_time: str = "now-6h",
        to_time: str = "now",
    ) -> bytes:
        """Render a panel as PNG image via Grafana Render API.

        Calls GET /render/d-solo/{uid}?panelId={panel_id}&width=...&height=...&from=...&to=...

        Args:
            dashboard_uid: Dashboard UID containing the panel.
            panel_id: ID of the panel to render.
            width: Image width in pixels.
            height: Image height in pixels.
            from_time: Start of time range (Grafana format).
            to_time: End of time range (Grafana format).

        Returns:
            Raw PNG image bytes.

        Raises:
            GrafanaNotFoundError: If panel or dashboard not found.
            GrafanaAPIError: If rendering fails.
        """
        params = {
            "panelId": str(panel_id),
            "width": str(width),
            "height": str(height),
            "from": from_time,
            "to": to_time,
        }
        response = self._request("GET", f"/render/d-solo/{dashboard_uid}", params=params)
        return response.content

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request to Grafana with error handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path relative to base URL.
            params: Optional query parameters.

        Returns:
            httpx Response object.

        Raises:
            GrafanaConnectionError: If connection fails.
            GrafanaNotFoundError: If resource not found (404).
            GrafanaAPIError: If Grafana returns an error status.
        """
        try:
            response = self._client.request(method, path, params=params)
        except httpx.ConnectError as e:
            logger.error("Cannot connect to Grafana at %s: %s", self._base_url, e)
            raise GrafanaConnectionError(f"Cannot connect to Grafana at {self._base_url}") from e
        except httpx.TimeoutException as e:
            logger.error("Grafana request timed out: %s", e)
            raise GrafanaConnectionError("Grafana request timed out") from e

        if response.status_code == 404:
            raise GrafanaNotFoundError("resource", path)

        if response.status_code >= 400:
            logger.error("Grafana API error: %d %s", response.status_code, response.text)
            raise GrafanaAPIError(
                f"Grafana returned {response.status_code}: {response.text}",
                status_code=502,
            )

        return response
