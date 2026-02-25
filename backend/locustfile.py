"""Locust load testing for Grafana PDF Reporter API.

Run with:
    locust -f backend/locustfile.py --host http://localhost:8000

Or headless:
    locust -f backend/locustfile.py --host http://localhost:8000 \
        --users 50 --spawn-rate 5 --run-time 5m --headless
"""

from __future__ import annotations

import logging

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)

# Default test credentials – override via environment variables if needed.
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


class GrafanaReporterUser(HttpUser):
    """Simulates a typical user of the Grafana PDF Reporter."""

    wait_time = between(1, 5)
    token: str | None = None

    def on_start(self) -> None:
        """Authenticate on session start."""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": DEFAULT_USERNAME,
                "password": DEFAULT_PASSWORD,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
        else:
            logger.warning("Login failed: %s", response.text)

    @property
    def auth_headers(self) -> dict[str, str]:
        """Return Authorization header dict."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def list_dashboards(self) -> None:
        """List Grafana dashboards (high frequency)."""
        self.client.get(
            "/api/v1/grafana/dashboards",
            headers=self.auth_headers,
            name="/api/v1/grafana/dashboards",
        )

    @task(3)
    def list_reports(self) -> None:
        """List user reports."""
        self.client.get(
            "/api/v1/reports",
            headers=self.auth_headers,
            name="/api/v1/reports",
        )

    @task(2)
    def get_report_stats(self) -> None:
        """Fetch report statistics."""
        self.client.get(
            "/api/v1/reports/stats",
            headers=self.auth_headers,
            name="/api/v1/reports/stats",
        )

    @task(1)
    def get_dashboard_detail(self) -> None:
        """Fetch a specific dashboard detail."""
        # First list dashboards to get a UID
        resp = self.client.get(
            "/api/v1/grafana/dashboards",
            headers=self.auth_headers,
            name="/api/v1/grafana/dashboards [for detail]",
        )
        if resp.status_code == 200:
            dashboards = resp.json()
            if isinstance(dashboards, list) and len(dashboards) > 0:
                uid = dashboards[0].get("uid", "")
                if uid:
                    self.client.get(
                        f"/api/v1/grafana/dashboards/{uid}",
                        headers=self.auth_headers,
                        name="/api/v1/grafana/dashboards/[uid]",
                    )

    @task(1)
    def generate_report(self) -> None:
        """Trigger a report generation (low frequency)."""
        # First get a dashboard for valid panel IDs
        resp = self.client.get(
            "/api/v1/grafana/dashboards",
            headers=self.auth_headers,
            name="/api/v1/grafana/dashboards [for report]",
        )
        if resp.status_code == 200:
            dashboards = resp.json()
            if isinstance(dashboards, list) and len(dashboards) > 0:
                uid = dashboards[0].get("uid", "")
                if uid:
                    self.client.post(
                        "/api/v1/reports/generate",
                        json={
                            "dashboard_uid": uid,
                            "title": "Load Test Report",
                            "panel_ids": [],
                            "time_range": {"from": "now-1h", "to": "now"},
                        },
                        headers=self.auth_headers,
                        name="/api/v1/reports/generate",
                    )

    @task(1)
    def get_user_profile(self) -> None:
        """Fetch current user profile."""
        self.client.get(
            "/api/v1/auth/me",
            headers=self.auth_headers,
            name="/api/v1/auth/me",
        )


class HealthCheckUser(HttpUser):
    """Lightweight user that only hits the health endpoint."""

    wait_time = between(2, 10)
    weight = 1

    @task
    def health_check(self) -> None:
        """Check application health."""
        self.client.get("/health", name="/health")
