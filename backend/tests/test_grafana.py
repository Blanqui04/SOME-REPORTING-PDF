"""Tests for Grafana proxy API endpoints."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.app.core.exceptions import GrafanaConnectionError, GrafanaNotFoundError


class TestListDashboards:
    """Tests for GET /api/v1/grafana/dashboards."""

    def test_list_dashboards(self, authenticated_client: TestClient) -> None:
        """Authenticated user can list dashboards."""
        response = authenticated_client.get("/api/v1/grafana/dashboards")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["uid"] == "test-dash-1"
        assert data[0]["title"] == "Test Dashboard 1"

    def test_list_dashboards_with_search(
        self,
        authenticated_client: TestClient,
        mock_grafana_client: MagicMock,
    ) -> None:
        """Search parameter is passed to Grafana client."""
        mock_grafana_client.list_dashboards.return_value = [
            {
                "uid": "test-dash-1",
                "title": "Test Dashboard 1",
                "url": "/d/test-dash-1",
                "tags": [],
            },
        ]
        response = authenticated_client.get("/api/v1/grafana/dashboards", params={"search": "Test"})
        assert response.status_code == 200
        mock_grafana_client.list_dashboards.assert_called_with(search="Test")

    def test_list_dashboards_unauthenticated(self, client: TestClient) -> None:
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/grafana/dashboards")
        assert response.status_code == 401


class TestGetDashboard:
    """Tests for GET /api/v1/grafana/dashboards/{uid}."""

    def test_get_dashboard(self, authenticated_client: TestClient) -> None:
        """Authenticated user can get dashboard details."""
        response = authenticated_client.get("/api/v1/grafana/dashboards/test-dash-1")
        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "test-dash-1"
        assert len(data["panels"]) == 3
        assert data["panels"][0]["title"] == "CPU Usage"

    def test_get_dashboard_not_found(
        self,
        authenticated_client: TestClient,
        mock_grafana_client: MagicMock,
    ) -> None:
        """Non-existent dashboard returns 404."""
        mock_grafana_client.get_dashboard.side_effect = GrafanaNotFoundError(
            "dashboard", "nonexistent"
        )
        response = authenticated_client.get("/api/v1/grafana/dashboards/nonexistent")
        assert response.status_code == 404

    def test_grafana_unavailable(
        self,
        authenticated_client: TestClient,
        mock_grafana_client: MagicMock,
    ) -> None:
        """Grafana connection error returns 502."""
        mock_grafana_client.get_dashboard.side_effect = GrafanaConnectionError()
        response = authenticated_client.get("/api/v1/grafana/dashboards/test-dash-1")
        assert response.status_code == 502


class TestRenderPanel:
    """Tests for GET /api/v1/grafana/dashboards/{uid}/panels/{panel_id}/render."""

    def test_render_panel(self, authenticated_client: TestClient) -> None:
        """Authenticated user can render a panel as PNG."""
        response = authenticated_client.get(
            "/api/v1/grafana/dashboards/test-dash-1/panels/1/render"
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0

    def test_render_panel_custom_params(
        self,
        authenticated_client: TestClient,
        mock_grafana_client: MagicMock,
    ) -> None:
        """Custom width/height/time params are passed to Grafana."""
        authenticated_client.get(
            "/api/v1/grafana/dashboards/test-dash-1/panels/1/render",
            params={
                "width": 800,
                "height": 400,
                "from_time": "now-24h",
                "to_time": "now",
            },
        )
        mock_grafana_client.render_panel.assert_called_with(
            dashboard_uid="test-dash-1",
            panel_id=1,
            width=800,
            height=400,
            from_time="now-24h",
            to_time="now",
        )
