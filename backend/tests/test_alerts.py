"""Tests for the Grafana Alerting webhook endpoint."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.api.v1.alerts import _extract_dashboard_uid
from backend.app.models.user import User

# ── Helper function tests ──────────────────────────────────────────

class TestExtractDashboardUID:
    """Tests for _extract_dashboard_uid utility."""

    def test_standard_url(self) -> None:
        url = "http://grafana:3000/d/abc123/my-dashboard"
        assert _extract_dashboard_uid(url) == "abc123"

    def test_url_with_query_params(self) -> None:
        url = "http://grafana:3000/d/xyz456/dash?orgId=1&from=now-1h"
        assert _extract_dashboard_uid(url) == "xyz456"

    def test_empty_string(self) -> None:
        assert _extract_dashboard_uid("") is None

    def test_no_d_path(self) -> None:
        url = "http://grafana:3000/dashboards"
        assert _extract_dashboard_uid(url) is None

    def test_uid_only(self) -> None:
        url = "http://grafana:3000/d/uid123/"
        assert _extract_dashboard_uid(url) == "uid123"

    def test_complex_uid(self) -> None:
        url = "http://localhost:3000/d/a1B2c3D4/some-dashboard-name?orgId=1"
        assert _extract_dashboard_uid(url) == "a1B2c3D4"


# ── Webhook endpoint tests ─────────────────────────────────────────

class TestGrafanaAlertWebhook:
    """Tests for POST /api/v1/webhooks/grafana-alerts."""

    def test_non_firing_alert_ignored(self, authenticated_client: TestClient) -> None:
        """Non-firing alerts should be skipped."""
        response = authenticated_client.post(
            "/api/v1/webhooks/grafana-alerts",
            json={
                "status": "resolved",
                "alerts": [],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["triggered"] == 0

    def test_firing_alert_with_dashboard_url(
        self,
        authenticated_client: TestClient,
        test_user: User,
        mock_grafana_client: MagicMock,
        db: Session,
    ) -> None:
        """Firing alert with a valid dashboard URL should trigger a report."""
        # Ensure user has admin role for the endpoint to find them
        test_user.role = "admin"
        db.commit()

        response = authenticated_client.post(
            "/api/v1/webhooks/grafana-alerts",
            json={
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "HighCPU"},
                        "annotations": {"summary": "CPU high", "dashboard_uid": ""},
                        "dashboardURL": "http://grafana:3000/d/test-dash-1/test",
                    },
                ],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["triggered"] == 1
        assert len(data["report_ids"]) == 1
        assert "test-dash-1" in data["dashboards"]

    def test_firing_alert_with_annotation_uid(
        self,
        authenticated_client: TestClient,
        test_user: User,
        mock_grafana_client: MagicMock,
        db: Session,
    ) -> None:
        """Firing alert with dashboard_uid in annotations should trigger report."""
        test_user.role = "admin"
        db.commit()

        response = authenticated_client.post(
            "/api/v1/webhooks/grafana-alerts",
            json={
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "HighMemory"},
                        "annotations": {
                            "summary": "Memory high",
                            "dashboard_uid": "test-dash-1",
                        },
                        "dashboardURL": "",
                    },
                ],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["triggered"] == 1

    def test_duplicate_dashboards_deduplicated(
        self,
        authenticated_client: TestClient,
        test_user: User,
        mock_grafana_client: MagicMock,
        db: Session,
    ) -> None:
        """Multiple alerts for the same dashboard should trigger only one report."""
        test_user.role = "admin"
        db.commit()

        response = authenticated_client.post(
            "/api/v1/webhooks/grafana-alerts",
            json={
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "Alert1"},
                        "annotations": {"dashboard_uid": "test-dash-1"},
                        "dashboardURL": "",
                    },
                    {
                        "status": "firing",
                        "labels": {"alertname": "Alert2"},
                        "annotations": {"dashboard_uid": "test-dash-1"},
                        "dashboardURL": "",
                    },
                ],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["triggered"] == 1

    def test_alert_without_dashboard_skipped(
        self,
        authenticated_client: TestClient,
    ) -> None:
        """Alerts with no extractable dashboard UID should be skipped."""
        response = authenticated_client.post(
            "/api/v1/webhooks/grafana-alerts",
            json={
                "status": "firing",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "NoDash"},
                        "annotations": {"summary": "no dashboard"},
                        "dashboardURL": "",
                    },
                ],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["triggered"] == 0

    def test_empty_alerts_array(self, authenticated_client: TestClient) -> None:
        """Empty alerts array should trigger nothing."""
        response = authenticated_client.post(
            "/api/v1/webhooks/grafana-alerts",
            json={
                "status": "firing",
                "alerts": [],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["triggered"] == 0
