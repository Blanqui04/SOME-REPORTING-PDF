"""Test fixtures for the Grafana PDF Reporter test suite."""

import uuid
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.deps import get_current_user, get_db, get_grafana_client, get_settings
from backend.app.core.config import Settings
from backend.app.core.security import hash_password
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.user import User
from backend.app.services.grafana_client import GrafanaClient


@pytest.fixture(name="settings")
def fixture_settings() -> Settings:
    """Return test settings with safe defaults."""
    return Settings(
        POSTGRES_PASSWORD="test",
        JWT_SECRET_KEY="test-secret-key-for-testing",
        GRAFANA_URL="http://mock-grafana:3000",
        GRAFANA_API_KEY="mock-api-key",
        DEBUG=True,
        POSTGRES_HOST="localhost",
        POSTGRES_DB="test_db",
    )


@pytest.fixture(name="engine")
def fixture_engine() -> Generator[Any, None, None]:
    """Create a test database engine using SQLite."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="db")
def fixture_db(engine: Any) -> Generator[Session, None, None]:
    """Yield a test database session with rollback."""
    test_session_factory = sessionmaker(bind=engine)
    session = test_session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(name="session_factory")
def fixture_session_factory(engine: Any) -> sessionmaker:
    """Return a sessionmaker for background task testing."""
    return sessionmaker(bind=engine)


@pytest.fixture(name="mock_grafana_client")
def fixture_mock_grafana_client() -> MagicMock:
    """Return a mock GrafanaClient that returns canned data."""
    client = MagicMock(spec=GrafanaClient)

    # Mock list_dashboards
    client.list_dashboards.return_value = [
        {
            "uid": "test-dash-1",
            "title": "Test Dashboard 1",
            "url": "/d/test-dash-1/test-dashboard-1",
            "tags": ["test"],
        },
        {
            "uid": "test-dash-2",
            "title": "Test Dashboard 2",
            "url": "/d/test-dash-2/test-dashboard-2",
            "tags": [],
        },
    ]

    # Mock get_dashboard
    client.get_dashboard.return_value = {
        "dashboard": {
            "uid": "test-dash-1",
            "title": "Test Dashboard 1",
            "tags": ["test"],
            "panels": [
                {"id": 1, "title": "CPU Usage", "type": "graph"},
                {"id": 2, "title": "Memory Usage", "type": "graph"},
                {"id": 3, "title": "Disk I/O", "type": "table"},
            ],
        },
        "meta": {
            "url": "/d/test-dash-1/test-dashboard-1",
        },
    }

    # Mock render_panel - return a minimal PNG header
    # PNG file signature
    png_signature = b"\x89PNG\r\n\x1a\n"
    client.render_panel.return_value = png_signature + b"\x00" * 100

    return client


@pytest.fixture(name="test_user")
def fixture_test_user(db: Session) -> User:
    """Create and return a test user in the database."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name="mock_celery_task", autouse=True)
def fixture_mock_celery_task() -> Generator[MagicMock, None, None]:
    """Mock the Celery generate_report_task to avoid needing Redis.

    This fixture is auto-used so all tests get the mock.
    """
    with (
        patch("backend.app.api.v1.reports.generate_report_task") as mock_task,
        patch("backend.app.api.v1.alerts.generate_report_task") as mock_alert_task,
    ):
        mock_task.delay.return_value = MagicMock(id="mock-celery-task-id")
        mock_alert_task.delay.return_value = MagicMock(id="mock-alert-task-id")
        yield mock_task


@pytest.fixture(name="client")
def fixture_client(
    db: Session,
    settings: Settings,
    mock_grafana_client: MagicMock,
) -> Generator[TestClient, None, None]:
    """Return a FastAPI TestClient with overridden dependencies."""
    app = create_app()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_grafana_client] = lambda: mock_grafana_client

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(name="authenticated_client")
def fixture_authenticated_client(
    db: Session,
    settings: Settings,
    mock_grafana_client: MagicMock,
    test_user: User,
) -> Generator[TestClient, None, None]:
    """Return a FastAPI TestClient with authentication pre-configured."""
    app = create_app()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_grafana_client] = lambda: mock_grafana_client
    app.dependency_overrides[get_current_user] = lambda: test_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def fixture_auth_headers(client: TestClient) -> dict[str, str]:
    """Register a test user, login, and return auth headers."""
    # Register
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "auth@example.com",
            "username": "authuser",
            "password": "authpassword123",
        },
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "authuser",
            "password": "authpassword123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
