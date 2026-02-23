"""Tests for report API endpoints."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.report import Report
from backend.app.models.user import User


def _create_report(db: Session, user: User, status: str = "completed") -> Report:
    """Helper to create a test report in the database."""
    report = Report(
        id=uuid.uuid4(),
        title="Test Report",
        dashboard_uid="test-dash-1",
        dashboard_title="Test Dashboard 1",
        panel_ids=[1, 2],
        time_range_from="now-6h",
        time_range_to="now",
        status=status,
        file_name="test_report.pdf",
        created_by_id=user.id,
        pdf_data=b"%PDF-1.4 test content" if status == "completed" else None,
        pdf_size_bytes=21 if status == "completed" else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


class TestGenerateReport:
    """Tests for POST /api/v1/reports/generate."""

    def test_generate_report(self, authenticated_client: TestClient) -> None:
        """Successful report generation returns 202 with pending status."""
        response = authenticated_client.post(
            "/api/v1/reports/generate",
            json={
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1, 2],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["dashboard_uid"] == "test-dash-1"
        assert data["panel_ids"] == [1, 2]
        assert "id" in data

    def test_generate_report_with_custom_params(self, authenticated_client: TestClient) -> None:
        """Report generation with custom parameters works."""
        response = authenticated_client.post(
            "/api/v1/reports/generate",
            json={
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1],
                "title": "Custom Report Title",
                "description": "A test report",
                "time_range_from": "now-24h",
                "time_range_to": "now",
                "width": 1200,
                "height": 600,
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["title"] == "Custom Report Title"
        assert data["description"] == "A test report"

    def test_generate_report_unauthenticated(self, client: TestClient) -> None:
        """Unauthenticated report generation returns 401."""
        response = client.post(
            "/api/v1/reports/generate",
            json={
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1],
            },
        )
        assert response.status_code == 401

    def test_generate_report_empty_panels(self, authenticated_client: TestClient) -> None:
        """Report generation with empty panel list returns 422."""
        response = authenticated_client.post(
            "/api/v1/reports/generate",
            json={
                "dashboard_uid": "test-dash-1",
                "panel_ids": [],
            },
        )
        assert response.status_code == 422


class TestListReports:
    """Tests for GET /api/v1/reports."""

    def test_list_reports_empty(self, authenticated_client: TestClient) -> None:
        """Empty report list returns 200 with empty items."""
        response = authenticated_client.get("/api/v1/reports")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_reports_with_data(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Report list with data returns paginated results."""
        _create_report(db, test_user)
        _create_report(db, test_user)

        response = authenticated_client.get("/api/v1/reports")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_reports_pagination(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Pagination parameters work correctly."""
        for _ in range(5):
            _create_report(db, test_user)

        response = authenticated_client.get("/api/v1/reports", params={"page": 1, "per_page": 2})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    def test_list_reports_filter_status(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Status filter returns only matching reports."""
        _create_report(db, test_user, status="completed")
        _create_report(db, test_user, status="pending")

        response = authenticated_client.get("/api/v1/reports", params={"status": "completed"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"


class TestGetReport:
    """Tests for GET /api/v1/reports/{report_id}."""

    def test_get_report(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Get a specific report by ID."""
        report = _create_report(db, test_user)

        response = authenticated_client.get(f"/api/v1/reports/{report.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(report.id)
        assert data["title"] == "Test Report"

    def test_get_report_not_found(self, authenticated_client: TestClient) -> None:
        """Non-existent report returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/api/v1/reports/{fake_id}")
        assert response.status_code == 404

    def test_get_report_other_user(self, authenticated_client: TestClient, db: Session) -> None:
        """Report owned by another user returns 404."""
        other_user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            username="otheruser",
            hashed_password="fakehash",
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        report = _create_report(db, other_user)

        response = authenticated_client.get(f"/api/v1/reports/{report.id}")
        assert response.status_code == 404


class TestDownloadReport:
    """Tests for GET /api/v1/reports/{report_id}/download."""

    def test_download_report_completed(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Completed report can be downloaded as PDF."""
        report = _create_report(db, test_user, status="completed")

        response = authenticated_client.get(f"/api/v1/reports/{report.id}/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]

    def test_download_report_pending(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Pending report download returns 409."""
        report = _create_report(db, test_user, status="pending")

        response = authenticated_client.get(f"/api/v1/reports/{report.id}/download")
        assert response.status_code == 409

    def test_download_report_not_found(self, authenticated_client: TestClient) -> None:
        """Non-existent report download returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/api/v1/reports/{fake_id}/download")
        assert response.status_code == 404
