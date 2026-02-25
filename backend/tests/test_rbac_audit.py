"""Tests for RBAC permissions and audit log."""

import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.permissions import UserRole, _get_role_level
from backend.app.models.user import User
from backend.app.services.audit_service import AuditService


class TestRoleHierarchy:
    """Tests for role hierarchy logic."""

    def test_admin_highest(self) -> None:
        """Admin has highest role level."""
        assert _get_role_level(UserRole.ADMIN.value) > _get_role_level(UserRole.EDITOR.value)
        assert _get_role_level(UserRole.ADMIN.value) > _get_role_level(UserRole.VIEWER.value)

    def test_editor_above_viewer(self) -> None:
        """Editor outranks viewer."""
        assert _get_role_level(UserRole.EDITOR.value) > _get_role_level(UserRole.VIEWER.value)

    def test_unknown_role_zero(self) -> None:
        """Unknown role returns 0."""
        assert _get_role_level("unknown") == 0


class TestAuditService:
    """Tests for the audit log service."""

    def test_create_audit_log(self, db: Session, test_user: User) -> None:
        """Audit log entry is created and persisted."""
        service = AuditService(db)
        entry = service.log(
            action="create",
            resource_type="report",
            resource_id=str(uuid.uuid4()),
            user_id=test_user.id,
            details="Generated a new report",
            ip_address="127.0.0.1",
        )
        assert entry.id is not None
        assert entry.action == "create"
        assert entry.resource_type == "report"
        assert entry.user_id == test_user.id

    def test_list_audit_logs(self, db: Session, test_user: User) -> None:
        """Audit logs can be listed with pagination."""
        service = AuditService(db)
        for _ in range(5):
            service.log(
                action="create",
                resource_type="report",
                user_id=test_user.id,
            )

        entries, total = service.list_logs(page=1, per_page=3)
        assert total == 5
        assert len(entries) == 3

    def test_filter_by_action(self, db: Session, test_user: User) -> None:
        """Audit logs can be filtered by action."""
        service = AuditService(db)
        service.log(action="create", resource_type="report", user_id=test_user.id)
        service.log(action="delete", resource_type="report", user_id=test_user.id)

        entries, total = service.list_logs(action="delete")
        assert total == 1
        assert entries[0].action == "delete"

    def test_filter_by_resource_type(self, db: Session, test_user: User) -> None:
        """Audit logs can be filtered by resource type."""
        service = AuditService(db)
        service.log(action="create", resource_type="report", user_id=test_user.id)
        service.log(action="create", resource_type="schedule", user_id=test_user.id)

        entries, total = service.list_logs(resource_type="schedule")
        assert total == 1
        assert entries[0].resource_type == "schedule"


class TestAuditAPI:
    """Tests for audit log API endpoints."""

    def test_audit_logs_requires_admin(self, authenticated_client: TestClient) -> None:
        """Non-admin user gets 403 on audit endpoint."""
        response = authenticated_client.get("/api/v1/audit")
        assert response.status_code == 403

    def test_audit_logs_admin_access(
        self, db: Session, settings: Settings, mock_grafana_client: MagicMock
    ) -> None:
        """Admin user can access audit logs."""
        from backend.app.api.deps import get_current_user, get_db, get_grafana_client, get_settings
        from backend.app.core.security import hash_password
        from backend.app.main import create_app

        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            username="adminuser",
            hashed_password=hash_password("adminpass123"),
            is_active=True,
            is_superuser=True,
            role="admin",
        )
        db.add(admin_user)
        db.commit()

        app = create_app()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_grafana_client] = lambda: mock_grafana_client
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with TestClient(app) as admin_client:
            response = admin_client.get("/api/v1/audit")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data

        app.dependency_overrides.clear()
