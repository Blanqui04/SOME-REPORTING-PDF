"""Tests for schedule API endpoints."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.schedule import Schedule
from backend.app.models.user import User


def _create_schedule(db: Session, user: User, **overrides: object) -> Schedule:
    """Helper to create a test schedule in the database."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Daily Report",
        "dashboard_uid": "test-dash-1",
        "panel_ids": [1, 2],
        "cron_expression": "0 8 * * *",
        "time_range_from": "now-24h",
        "time_range_to": "now",
        "is_active": True,
        "user_id": user.id,
        "language": "ca",
        "width": 1000,
        "height": 500,
        "dashboard_title": "Test Dashboard 1",
    }
    defaults.update(overrides)
    schedule = Schedule(**defaults)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


class TestCreateSchedule:
    """Tests for POST /api/v1/schedules."""

    def test_create_schedule(self, authenticated_client: TestClient) -> None:
        """Successful schedule creation returns 201."""
        response = authenticated_client.post(
            "/api/v1/schedules",
            json={
                "name": "Weekly Report",
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1, 2],
                "cron_expression": "0 8 * * 1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Weekly Report"
        assert data["dashboard_uid"] == "test-dash-1"
        assert data["cron_expression"] == "0 8 * * 1"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_schedule_with_email(self, authenticated_client: TestClient) -> None:
        """Schedule with email recipients is accepted."""
        response = authenticated_client.post(
            "/api/v1/schedules",
            json={
                "name": "Email Report",
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1],
                "cron_expression": "0 9 * * *",
                "email_recipients": ["admin@example.com", "user@example.com"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email_recipients"] == ["admin@example.com", "user@example.com"]

    def test_create_schedule_with_webhook(self, authenticated_client: TestClient) -> None:
        """Schedule with webhook URL is accepted."""
        response = authenticated_client.post(
            "/api/v1/schedules",
            json={
                "name": "Webhook Report",
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1],
                "cron_expression": "0 10 * * *",
                "webhook_url": "https://hooks.example.com/report",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["webhook_url"] == "https://hooks.example.com/report"

    def test_create_schedule_unauthenticated(self, client: TestClient) -> None:
        """Unauthenticated schedule creation returns 401."""
        response = client.post(
            "/api/v1/schedules",
            json={
                "name": "Fail",
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1],
                "cron_expression": "0 8 * * *",
            },
        )
        assert response.status_code == 401

    def test_create_schedule_empty_name(self, authenticated_client: TestClient) -> None:
        """Empty name returns 422."""
        response = authenticated_client.post(
            "/api/v1/schedules",
            json={
                "name": "",
                "dashboard_uid": "test-dash-1",
                "panel_ids": [1],
                "cron_expression": "0 8 * * *",
            },
        )
        assert response.status_code == 422

    def test_create_schedule_empty_panels(self, authenticated_client: TestClient) -> None:
        """Empty panel list returns 422."""
        response = authenticated_client.post(
            "/api/v1/schedules",
            json={
                "name": "Fail",
                "dashboard_uid": "test-dash-1",
                "panel_ids": [],
                "cron_expression": "0 8 * * *",
            },
        )
        assert response.status_code == 422


class TestListSchedules:
    """Tests for GET /api/v1/schedules."""

    def test_list_schedules_empty(self, authenticated_client: TestClient) -> None:
        """Empty schedule list returns 200."""
        response = authenticated_client.get("/api/v1/schedules")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_schedules_with_data(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Schedule list returns created schedules."""
        _create_schedule(db, test_user, name="Schedule 1")
        _create_schedule(db, test_user, name="Schedule 2")

        response = authenticated_client.get("/api/v1/schedules")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_schedules_active_only(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Active filter returns only active schedules."""
        _create_schedule(db, test_user, is_active=True, name="Active")
        _create_schedule(db, test_user, is_active=False, name="Inactive")

        response = authenticated_client.get("/api/v1/schedules", params={"active_only": True})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Active"


class TestGetSchedule:
    """Tests for GET /api/v1/schedules/{schedule_id}."""

    def test_get_schedule(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Get existing schedule returns 200."""
        schedule = _create_schedule(db, test_user)
        response = authenticated_client.get(f"/api/v1/schedules/{schedule.id}")
        assert response.status_code == 200
        assert response.json()["id"] == str(schedule.id)

    def test_get_schedule_not_found(self, authenticated_client: TestClient) -> None:
        """Non-existent schedule returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/api/v1/schedules/{fake_id}")
        assert response.status_code == 404


class TestUpdateSchedule:
    """Tests for PUT /api/v1/schedules/{schedule_id}."""

    def test_update_schedule(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Update schedule name returns 200."""
        schedule = _create_schedule(db, test_user)
        response = authenticated_client.put(
            f"/api/v1/schedules/{schedule.id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_update_schedule_cron(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Update cron expression recalculates next_run_at."""
        schedule = _create_schedule(db, test_user)
        response = authenticated_client.put(
            f"/api/v1/schedules/{schedule.id}",
            json={"cron_expression": "30 12 * * *"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cron_expression"] == "30 12 * * *"
        assert data["next_run_at"] is not None


class TestToggleSchedule:
    """Tests for POST /api/v1/schedules/{schedule_id}/toggle."""

    def test_toggle_schedule(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Toggle active schedule to inactive."""
        schedule = _create_schedule(db, test_user, is_active=True)
        response = authenticated_client.post(f"/api/v1/schedules/{schedule.id}/toggle")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_toggle_schedule_back(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Toggle inactive schedule back to active."""
        schedule = _create_schedule(db, test_user, is_active=False)
        response = authenticated_client.post(f"/api/v1/schedules/{schedule.id}/toggle")
        assert response.status_code == 200
        assert response.json()["is_active"] is True


class TestDeleteSchedule:
    """Tests for DELETE /api/v1/schedules/{schedule_id}."""

    def test_delete_schedule(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Delete a schedule returns 204."""
        schedule = _create_schedule(db, test_user)
        response = authenticated_client.delete(f"/api/v1/schedules/{schedule.id}")
        assert response.status_code == 204

    def test_delete_schedule_not_found(self, authenticated_client: TestClient) -> None:
        """Delete non-existent schedule returns 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.delete(f"/api/v1/schedules/{fake_id}")
        assert response.status_code == 404
