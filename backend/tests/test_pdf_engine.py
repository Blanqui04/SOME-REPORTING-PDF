"""Tests for the PDF rendering engine."""

from pathlib import Path

import pytest

from backend.app.core.exceptions import PDFRenderError
from backend.app.services.pdf_engine import PanelImage, PDFEngine, ReportContext

TEMPLATE_DIR = str(Path(__file__).resolve().parents[1] / "app" / "templates")


@pytest.fixture(name="pdf_engine")
def fixture_pdf_engine() -> PDFEngine:
    """Return a PDFEngine initialized with the project templates."""
    return PDFEngine(template_dir=TEMPLATE_DIR)


@pytest.fixture(name="sample_context")
def fixture_sample_context() -> ReportContext:
    """Return a sample ReportContext for testing."""
    return ReportContext(
        report_title="Test Report",
        dashboard_title="Test Dashboard",
        dashboard_uid="test-uid",
        generated_at="2026-02-23T10:00:00+00:00",
        time_range_from="now-6h",
        time_range_to="now",
        panels=[
            PanelImage(
                panel_id=1,
                title="CPU Usage",
                image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            ),
        ],
        description="A test report for unit testing",
        company_name="Test Corp",
    )


class TestPDFEngine:
    """Tests for the PDFEngine service."""

    def test_render_html_template(
        self, pdf_engine: PDFEngine, sample_context: ReportContext
    ) -> None:
        """HTML rendering produces expected content."""
        template_vars = {
            "report_title": sample_context.report_title,
            "dashboard_title": sample_context.dashboard_title,
            "dashboard_uid": sample_context.dashboard_uid,
            "generated_at": sample_context.generated_at,
            "time_range_from": sample_context.time_range_from,
            "time_range_to": sample_context.time_range_to,
            "panels": sample_context.panels,
            "description": sample_context.description,
            "company_name": sample_context.company_name,
        }
        html = pdf_engine._render_html("report.html", template_vars)

        assert "Test Report" in html
        assert "Test Dashboard" in html
        assert "test-uid" in html
        assert "CPU Usage" in html
        assert "Test Corp" in html
        assert "A test report for unit testing" in html

    def test_html_to_pdf_produces_bytes(self, pdf_engine: PDFEngine) -> None:
        """WeasyPrint produces valid PDF bytes from basic HTML."""
        html = "<html><body><h1>Test</h1></body></html>"
        pdf_bytes = pdf_engine._html_to_pdf(html)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 100

    def test_render_report_full(self, pdf_engine: PDFEngine, sample_context: ReportContext) -> None:
        """Full render_report produces valid PDF bytes."""
        pdf_bytes = pdf_engine.render_report(sample_context)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 100

    def test_render_report_empty_panels(self, pdf_engine: PDFEngine) -> None:
        """Report with no panels still produces valid PDF."""
        context = ReportContext(
            report_title="Empty Report",
            dashboard_title="Empty Dashboard",
            dashboard_uid="empty-uid",
            generated_at="2026-02-23T10:00:00+00:00",
            time_range_from="now-1h",
            time_range_to="now",
            panels=[],
        )
        pdf_bytes = pdf_engine.render_report(context)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_render_report_missing_image(self, pdf_engine: PDFEngine) -> None:
        """Panel with empty image_base64 shows placeholder."""
        context = ReportContext(
            report_title="Missing Image Report",
            dashboard_title="Test Dashboard",
            dashboard_uid="test-uid",
            generated_at="2026-02-23T10:00:00+00:00",
            time_range_from="now-6h",
            time_range_to="now",
            panels=[
                PanelImage(panel_id=1, title="Broken Panel", image_base64=""),
            ],
        )
        pdf_bytes = pdf_engine.render_report(context)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_invalid_template_raises(self) -> None:
        """Non-existent template directory raises PDFRenderError."""
        engine = PDFEngine(template_dir="/nonexistent/path")
        context = ReportContext(
            report_title="Error Report",
            dashboard_title="Test",
            dashboard_uid="test",
            generated_at="2026-02-23T10:00:00+00:00",
            time_range_from="now-6h",
            time_range_to="now",
        )
        with pytest.raises(PDFRenderError):
            engine.render_report(context)
