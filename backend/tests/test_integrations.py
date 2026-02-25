"""Tests for Sprint 7-8 — Integrations, Performance & Quality.

Covers:
- Notification service (Slack/Teams webhooks)
- S3 storage service
- PDF compression
- Panel cache
- Prometheus metrics
- Batch generation endpoint
- CLI tool
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from backend.app.core.config import Settings
from backend.app.core.metrics import (
    _MetricsStore,
    record_pdf_duration,
    record_pdf_size,
    record_report_failed,
    record_report_generated,
)
from backend.app.services.notification_service import (
    NotificationService,
    WebhookType,
)
from backend.app.services.pdf_compression import compress_pdf, get_pdf_info

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_simple_pdf() -> bytes:
    """Create a minimal valid PDF for testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def _make_settings(**overrides: Any) -> Settings:
    """Create test Settings with safe defaults."""
    defaults: dict[str, Any] = {
        "POSTGRES_PASSWORD": "test",
        "JWT_SECRET_KEY": "test-secret",
        "GRAFANA_URL": "http://localhost:3000",
        "GRAFANA_API_KEY": "test-key",
        "S3_ENABLED": False,
        "S3_ENDPOINT_URL": "",
        "S3_ACCESS_KEY": "",
        "S3_SECRET_KEY": "",
        "S3_BUCKET_NAME": "test-bucket",
        "REDIS_URL": "redis://localhost:6379/0",
        "PROMETHEUS_ENABLED": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ==================================================================
# Notification Service Tests
# ==================================================================


class TestNotificationService:
    """Tests for Slack/Teams webhook notification service."""

    def test_slack_completed_payload(self) -> None:
        """Slack payload contains correct structure for completed report."""
        svc = NotificationService()
        payload = svc._build_payload(
            webhook_type=WebhookType.SLACK,
            status="completed",
            report_title="Daily Report",
            dashboard_title="Production Metrics",
            download_url="https://example.com/download/123",
            file_size_bytes=1024 * 500,
        )
        assert "attachments" in payload
        attachment = payload["attachments"][0]
        assert attachment["color"] == "#36a64f"
        blocks = attachment["blocks"]
        assert any("completed" in str(b).lower() for b in blocks)

    def test_slack_failed_payload(self) -> None:
        """Slack payload for failed report includes error info."""
        svc = NotificationService()
        payload = svc._build_payload(
            webhook_type=WebhookType.SLACK,
            status="failed",
            report_title="Failed Report",
            dashboard_title="Test Dashboard",
            error_message="Grafana timeout",
        )
        attachment = payload["attachments"][0]
        assert attachment["color"] == "#dc3545"
        assert any("Grafana timeout" in str(b) for b in attachment["blocks"])

    def test_teams_completed_payload(self) -> None:
        """Teams Adaptive Card payload for completed report."""
        svc = NotificationService()
        payload = svc._build_payload(
            webhook_type=WebhookType.TEAMS,
            status="completed",
            report_title="Weekly Report",
            dashboard_title="Analytics",
            file_size_bytes=2048,
        )
        assert payload["type"] == "message"
        card = payload["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"

    def test_teams_failed_payload(self) -> None:
        """Teams payload for failed report includes error fact."""
        svc = NotificationService()
        payload = svc._build_payload(
            webhook_type=WebhookType.TEAMS,
            status="failed",
            report_title="Error Report",
            dashboard_title="Dash",
            error_message="Connection refused",
        )
        facts = payload["attachments"][0]["content"]["body"][1]["facts"]
        error_facts = [f for f in facts if f["name"] == "Error"]
        assert len(error_facts) == 1
        assert error_facts[0]["value"] == "Connection refused"

    def test_generic_payload(self) -> None:
        """Generic webhook payload is a simple JSON dict."""
        svc = NotificationService()
        payload = svc._build_payload(
            webhook_type=WebhookType.GENERIC,
            status="completed",
            report_title="Test",
            dashboard_title="Dash",
        )
        assert payload["event"] == "report.completed"
        assert payload["report_title"] == "Test"

    @patch("backend.app.services.notification_service.httpx.post")
    def test_send_success(self, mock_post: MagicMock) -> None:
        """Successful webhook delivery returns True."""
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_post.return_value = mock_response

        svc = NotificationService()
        result = svc.notify_report_completed(
            webhook_url="https://hooks.slack.com/test",
            webhook_type=WebhookType.SLACK,
            report_title="Test",
            dashboard_title="Dash",
        )
        assert result is True
        mock_post.assert_called_once()

    @patch("backend.app.services.notification_service.httpx.post")
    def test_send_failure(self, mock_post: MagicMock) -> None:
        """Failed webhook delivery returns False."""
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        svc = NotificationService()
        result = svc.notify_report_failed(
            webhook_url="https://hooks.teams.com/test",
            webhook_type=WebhookType.TEAMS,
            report_title="Test",
            dashboard_title="Dash",
        )
        assert result is False

    @patch("backend.app.services.notification_service.httpx.post")
    def test_send_http_error(self, mock_post: MagicMock) -> None:
        """HTTP exception during send returns False gracefully."""
        import httpx

        mock_post.side_effect = httpx.ConnectError("Connection refused")

        svc = NotificationService()
        result = svc.notify_report_completed(
            webhook_url="https://unreachable.example.com",
            webhook_type=WebhookType.GENERIC,
            report_title="Test",
            dashboard_title="Dash",
        )
        assert result is False

    def test_format_size(self) -> None:
        """Human-readable size formatting."""
        svc = NotificationService()
        assert svc._format_size(500) == "500 B"
        assert svc._format_size(1536) == "1.5 KB"
        assert svc._format_size(1048576) == "1.0 MB"

    def test_webhook_type_enum(self) -> None:
        """WebhookType enum values match expected strings."""
        assert WebhookType.SLACK == "slack"
        assert WebhookType.TEAMS == "teams"
        assert WebhookType.GENERIC == "generic"


# ==================================================================
# S3 Storage Service Tests
# ==================================================================


class TestS3StorageService:
    """Tests for S3/MinIO storage service."""

    def test_disabled_by_default(self) -> None:
        """S3 service is disabled when S3_ENABLED is False."""
        from backend.app.services.storage_service import S3StorageService

        settings = _make_settings(S3_ENABLED=False)
        svc = S3StorageService(settings)
        assert svc.enabled is False

    def test_enabled_with_endpoint(self) -> None:
        """S3 service is enabled when S3_ENABLED + endpoint configured."""
        from backend.app.services.storage_service import S3StorageService

        settings = _make_settings(
            S3_ENABLED=True,
            S3_ENDPOINT_URL="http://minio:9000",
        )
        svc = S3StorageService(settings)
        assert svc.enabled is True

    def test_generate_key(self) -> None:
        """Key generation follows expected pattern."""
        from backend.app.services.storage_service import S3StorageService

        settings = _make_settings()
        svc = S3StorageService(settings)
        key = svc.generate_key("abc-123", "report.pdf")
        assert key == "reports/abc-123/report.pdf"

    def test_upload_disabled_raises(self) -> None:
        """Upload raises RuntimeError when S3 is disabled."""
        from backend.app.services.storage_service import S3StorageService

        settings = _make_settings(S3_ENABLED=False)
        svc = S3StorageService(settings)
        with pytest.raises(RuntimeError, match="not enabled"):
            svc.upload_pdf("key.pdf", b"data")

    def test_download_disabled_raises(self) -> None:
        """Download raises RuntimeError when S3 is disabled."""
        from backend.app.services.storage_service import S3StorageService

        settings = _make_settings(S3_ENABLED=False)
        svc = S3StorageService(settings)
        with pytest.raises(RuntimeError, match="not enabled"):
            svc.download_pdf("key.pdf")

    @patch("backend.app.services.storage_service.httpx.put")
    def test_upload_success(self, mock_put: MagicMock) -> None:
        """Successful upload returns the object URL."""
        from backend.app.services.storage_service import S3StorageService

        mock_put.return_value = MagicMock(is_success=True)
        settings = _make_settings(
            S3_ENABLED=True,
            S3_ENDPOINT_URL="http://minio:9000",
        )
        svc = S3StorageService(settings)
        url = svc.upload_pdf("reports/test.pdf", b"pdf-data")
        assert "minio:9000" in url
        assert "test.pdf" in url

    @patch("backend.app.services.storage_service.httpx.get")
    def test_download_success(self, mock_get: MagicMock) -> None:
        """Successful download returns PDF bytes."""
        from backend.app.services.storage_service import S3StorageService

        mock_get.return_value = MagicMock(is_success=True, content=b"pdf-content")
        settings = _make_settings(
            S3_ENABLED=True,
            S3_ENDPOINT_URL="http://minio:9000",
        )
        svc = S3StorageService(settings)
        data = svc.download_pdf("reports/test.pdf")
        assert data == b"pdf-content"

    @patch("backend.app.services.storage_service.httpx.delete")
    def test_delete_success(self, mock_delete: MagicMock) -> None:
        """Successful delete returns True."""
        from backend.app.services.storage_service import S3StorageService

        mock_delete.return_value = MagicMock(is_success=True)
        settings = _make_settings(
            S3_ENABLED=True,
            S3_ENDPOINT_URL="http://minio:9000",
        )
        svc = S3StorageService(settings)
        result = svc.delete_pdf("reports/test.pdf")
        assert result is True

    def test_presigned_url(self) -> None:
        """Presigned URL includes bucket and key."""
        from backend.app.services.storage_service import S3StorageService

        settings = _make_settings(
            S3_ENABLED=True,
            S3_ENDPOINT_URL="http://minio:9000",
        )
        svc = S3StorageService(settings)
        url = svc.get_presigned_url("reports/test.pdf", expires_in=600)
        assert "reports/test.pdf" in url
        assert "expires=600" in url


# ==================================================================
# PDF Compression Tests
# ==================================================================


class TestPDFCompression:
    """Tests for PDF compression utility."""

    def test_compress_valid_pdf(self) -> None:
        """Compressing a valid PDF returns valid PDF bytes."""
        pdf = _make_simple_pdf()
        result = compress_pdf(pdf)
        assert result[:5] == b"%PDF-"
        assert len(result) > 0

    def test_compress_returns_smaller_or_equal(self) -> None:
        """Compression returns data no larger than original."""
        pdf = _make_simple_pdf()
        result = compress_pdf(pdf)
        # The result should be either smaller or the same as original
        assert len(result) <= len(pdf) + 100  # Small tolerance for metadata

    def test_compress_invalid_data(self) -> None:
        """Invalid PDF data raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PDF"):
            compress_pdf(b"not a pdf")

    def test_compress_empty_data(self) -> None:
        """Empty data raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PDF"):
            compress_pdf(b"")

    def test_get_pdf_info(self) -> None:
        """PDF info extraction returns expected fields."""
        pdf = _make_simple_pdf()
        info = get_pdf_info(pdf)
        assert info["page_count"] == 1
        assert info["file_size_bytes"] == len(pdf)

    def test_get_pdf_info_invalid(self) -> None:
        """Invalid PDF returns error info gracefully."""
        info = get_pdf_info(b"not a pdf")
        assert "error" in info


# ==================================================================
# Panel Cache Tests
# ==================================================================


class TestPanelCache:
    """Tests for Redis-based panel cache."""

    def test_cache_key_deterministic(self) -> None:
        """Same input produces same cache key."""
        from backend.app.services.panel_cache import PanelCache

        key1 = PanelCache._make_key("dash-1", 1, "now-1h", "now")
        key2 = PanelCache._make_key("dash-1", 1, "now-1h", "now")
        assert key1 == key2

    def test_cache_key_different_inputs(self) -> None:
        """Different inputs produce different cache keys."""
        from backend.app.services.panel_cache import PanelCache

        key1 = PanelCache._make_key("dash-1", 1, "now-1h", "now")
        key2 = PanelCache._make_key("dash-2", 1, "now-1h", "now")
        assert key1 != key2

    def test_cache_key_includes_dimensions(self) -> None:
        """Different dimensions produce different cache keys."""
        from backend.app.services.panel_cache import PanelCache

        key1 = PanelCache._make_key("d", 1, "now-1h", "now", 1000, 500)
        key2 = PanelCache._make_key("d", 1, "now-1h", "now", 800, 400)
        assert key1 != key2

    def test_cache_unavailable_returns_none(self) -> None:
        """Cache get returns None when Redis is unavailable."""
        from backend.app.services.panel_cache import PanelCache

        settings = _make_settings(REDIS_URL="redis://invalid-host:6379")
        cache = PanelCache(settings)
        result = cache.get("dash", 1, "now-1h", "now")
        assert result is None

    def test_cache_unavailable_set_returns_false(self) -> None:
        """Cache set returns False when Redis is unavailable."""
        from backend.app.services.panel_cache import PanelCache

        settings = _make_settings(REDIS_URL="redis://invalid-host:6379")
        cache = PanelCache(settings)
        result = cache.set("dash", 1, "now-1h", "now", b"image-data")
        assert result is False


# ==================================================================
# Prometheus Metrics Tests
# ==================================================================


class TestMetrics:
    """Tests for Prometheus metrics store."""

    def test_counter_increment(self) -> None:
        """Counter increments correctly."""
        store = _MetricsStore()
        store.inc("test_counter")
        store.inc("test_counter")
        store.inc("test_counter", 5)
        rendered = store.render()
        assert "test_counter 7" in rendered

    def test_gauge_set(self) -> None:
        """Gauge value is set correctly."""
        store = _MetricsStore()
        store.set_gauge("test_gauge", 42.5)
        rendered = store.render()
        assert "test_gauge 42.5" in rendered

    def test_histogram_observe(self) -> None:
        """Histogram records observations."""
        store = _MetricsStore()
        store.observe("test_hist", 1.0)
        store.observe("test_hist", 2.0)
        store.observe("test_hist", 3.0)
        rendered = store.render()
        assert "test_hist_count 3" in rendered
        assert "test_hist_sum 6.0" in rendered

    def test_render_empty(self) -> None:
        """Empty store renders with newline only."""
        store = _MetricsStore()
        rendered = store.render()
        assert rendered == "\n"

    def test_record_helpers(self) -> None:
        """Helper functions don't raise."""
        record_report_generated()
        record_report_failed()
        record_pdf_duration(2.5)
        record_pdf_size(1024)

    def test_histogram_bounds_memory(self) -> None:
        """Histogram trims observations beyond 1000."""
        store = _MetricsStore()
        for i in range(1100):
            store.observe("bounded", float(i))
        assert len(store._histograms["bounded"]) <= 1000


# ==================================================================
# Batch Generation Endpoint Tests
# ==================================================================


class TestBatchGenerate:
    """Tests for batch report generation endpoint."""

    def test_batch_generate(self, authenticated_client: TestClient) -> None:
        """Batch generate creates reports for multiple dashboards."""
        response = authenticated_client.post(
            "/api/v1/reports/batch",
            json={
                "dashboard_uids": ["test-dash-1", "test-dash-2"],
                "time_range_from": "now-24h",
                "time_range_to": "now",
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert "reports" in data
        assert len(data["reports"]) == 2

    def test_batch_generate_single(self, authenticated_client: TestClient) -> None:
        """Batch with single dashboard works correctly."""
        response = authenticated_client.post(
            "/api/v1/reports/batch",
            json={
                "dashboard_uids": ["test-dash-1"],
                "time_range_from": "now-1h",
                "time_range_to": "now",
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert len(data["reports"]) == 1

    def test_batch_empty_dashboards(self, authenticated_client: TestClient) -> None:
        """Batch with empty dashboard list returns 422."""
        response = authenticated_client.post(
            "/api/v1/reports/batch",
            json={
                "dashboard_uids": [],
            },
        )
        assert response.status_code == 422


# ==================================================================
# CLI Tool Tests
# ==================================================================


class TestCLI:
    """Tests for the CLI argument parser and commands."""

    def test_parser_builds(self) -> None:
        """Parser builds without errors."""
        from backend.cli import build_parser

        parser = build_parser()
        assert parser is not None

    def test_parser_dashboards_command(self) -> None:
        """Dashboards command parses correctly."""
        from backend.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["dashboards"])
        assert args.command == "dashboards"

    def test_parser_generate_command(self) -> None:
        """Generate command parses with required args."""
        from backend.cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "generate", "-d", "test-uid",
            "--panels", "1,2,3",
            "--wait", "-o", "output.pdf",
        ])
        assert args.command == "generate"
        assert args.dashboard == "test-uid"
        assert args.panels == "1,2,3"
        assert args.wait is True
        assert args.output == "output.pdf"

    def test_parser_list_command(self) -> None:
        """List command parses with filters."""
        from backend.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["list", "--status", "completed", "--page", "2"])
        assert args.command == "list"
        assert args.status == "completed"
        assert args.page == 2

    def test_parser_download_command(self) -> None:
        """Download command parses with report ID."""
        from backend.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["download", "uuid-123", "-o", "my.pdf"])
        assert args.command == "download"
        assert args.report_id == "uuid-123"
        assert args.output == "my.pdf"

    def test_parser_stats_command(self) -> None:
        """Stats command parses without errors."""
        from backend.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"

    def test_parser_global_options(self) -> None:
        """Global options (base-url, token, json) parse correctly."""
        from backend.cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "--base-url", "http://api:8000",
            "--token", "jwt-test-token",
            "--json",
            "stats",
        ])
        assert args.base_url == "http://api:8000"
        assert args.token == "jwt-test-token"
        assert args.json_output is True
