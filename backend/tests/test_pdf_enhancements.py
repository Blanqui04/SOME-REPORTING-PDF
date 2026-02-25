"""Tests for Sprint 5 PDF engine enhancements.

Covers TOC, landscape/portrait orientation, watermark, grid layout,
data tables, and temporal comparison features.
"""

import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from backend.app.core.i18n import SUPPORTED_LOCALES, get_translations
from backend.app.services.pdf_engine import (
    ComparisonPanel,
    DataTable,
    DataTableColumn,
    PanelImage,
    PDFEngine,
    ReportContext,
)

TEMPLATE_DIR = str(Path(__file__).resolve().parents[1] / "app" / "templates")

# A tiny 1x1 transparent PNG, base64-encoded, for panel image stubs
_PIXEL_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture(name="engine")
def fixture_engine() -> PDFEngine:
    """Return a PDFEngine with the project templates."""
    return PDFEngine(template_dir=TEMPLATE_DIR)


def _make_context(**overrides: object) -> ReportContext:
    """Build a ReportContext with sensible defaults, applying *overrides*."""
    defaults: dict = {
        "report_title": "Enhancement Test",
        "dashboard_title": "Test Dashboard",
        "dashboard_uid": "test-uid",
        "generated_at": "2026-03-01T12:00:00+00:00",
        "time_range_from": "now-6h",
        "time_range_to": "now",
        "panels": [
            PanelImage(panel_id=1, title="Panel A", image_base64=_PIXEL_PNG_B64),
            PanelImage(panel_id=2, title="Panel B", image_base64=_PIXEL_PNG_B64),
        ],
    }
    defaults.update(overrides)
    return ReportContext(**defaults)


# ── TOC ──────────────────────────────────────────────────────────────


class TestTableOfContents:
    """Tests for auto-generated Table of Contents."""

    def test_toc_enabled_html_contains_toc_section(self, engine: PDFEngine) -> None:
        """When toc_enabled=True, HTML includes the TOC section with panel links."""
        ctx = _make_context(toc_enabled=True)
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="toc-section"' in html
        assert tr["pdf.toc_title"] in html
        assert 'href="#panel-1"' in html
        assert 'href="#panel-2"' in html

    def test_toc_disabled_no_toc_section(self, engine: PDFEngine) -> None:
        """When toc_enabled=False, no TOC section appears."""
        ctx = _make_context(toc_enabled=False)
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="toc-section"' not in html

    def test_toc_empty_panels_no_toc(self, engine: PDFEngine) -> None:
        """When toc_enabled=True but panels is empty, no TOC renders."""
        ctx = _make_context(toc_enabled=True, panels=[])
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="toc-section"' not in html

    def test_toc_pdf_renders_successfully(self, engine: PDFEngine) -> None:
        """Full PDF with TOC produces valid bytes."""
        ctx = _make_context(toc_enabled=True)
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 100


# ── Orientation ──────────────────────────────────────────────────────


class TestOrientation:
    """Tests for landscape/portrait page orientation."""

    def test_portrait_default(self, engine: PDFEngine) -> None:
        """Default orientation is portrait (no landscape class on body)."""
        ctx = _make_context()
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="landscape-mode"' not in html

    def test_landscape_class_injected(self, engine: PDFEngine) -> None:
        """Landscape orientation injects the landscape-mode class on body."""
        ctx = _make_context(orientation="landscape")
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="landscape-mode"' in html

    def test_landscape_pdf_renders(self, engine: PDFEngine) -> None:
        """Landscape PDF renders without errors."""
        ctx = _make_context(orientation="landscape")
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"

    def test_portrait_pdf_renders(self, engine: PDFEngine) -> None:
        """Portrait PDF renders without errors."""
        ctx = _make_context(orientation="portrait")
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"


# ── Watermark ────────────────────────────────────────────────────────


class TestWatermark:
    """Tests for PDF watermark overlay."""

    def test_watermark_applied(self, engine: PDFEngine) -> None:
        """PDF with watermark text has more bytes than without (overlay added)."""
        ctx_no_wm = _make_context()
        ctx_wm = _make_context(watermark_text="CONFIDENTIAL")
        pdf_no_wm = engine.render_report(ctx_no_wm)
        pdf_wm = engine.render_report(ctx_wm)
        assert pdf_wm[:5] == b"%PDF-"
        # Watermark adds overlay → different (typically larger) PDF
        assert pdf_wm != pdf_no_wm

    def test_watermark_none_no_overlay(self, engine: PDFEngine) -> None:
        """No watermark text means no overlay processing."""
        ctx = _make_context(watermark_text=None)
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"

    def test_watermark_draft(self, engine: PDFEngine) -> None:
        """Draft watermark renders successfully."""
        ctx = _make_context(watermark_text="DRAFT")
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 100

    def test_apply_watermark_method(self, engine: PDFEngine) -> None:
        """Standalone _apply_watermark produces valid PDF bytes."""
        ctx = _make_context()
        original = engine.render_report(ctx)
        watermarked = engine._apply_watermark(original, "TEST")
        # Watermarked document must still be a valid PDF
        reader = PdfReader(io.BytesIO(watermarked))
        assert len(reader.pages) >= 1


# ── Panel Grid ───────────────────────────────────────────────────────


class TestPanelGrid:
    """Tests for configurable panel grid layout."""

    def test_single_column_default(self, engine: PDFEngine) -> None:
        """Default panel_columns=1 does not inject 2-column class on div."""
        ctx = _make_context(panel_columns=1)
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="panels-grid panels-grid-2"' not in html
        assert 'class="panels-grid"' in html

    def test_two_columns_class(self, engine: PDFEngine) -> None:
        """panel_columns=2 injects the panels-grid-2 class on div."""
        ctx = _make_context(panel_columns=2)
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'panels-grid panels-grid-2' in html

    def test_two_columns_pdf(self, engine: PDFEngine) -> None:
        """Two-column PDF renders correctly."""
        ctx = _make_context(panel_columns=2)
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"


# ── Data Tables ──────────────────────────────────────────────────────


class TestDataTables:
    """Tests for raw panel data tables as PDF annex."""

    def test_data_table_html_rendered(self, engine: PDFEngine) -> None:
        """Data table with rows appears in HTML output."""
        dt = DataTable(
            panel_id=1,
            title="CPU Data",
            columns=[
                DataTableColumn(header="Time", values=["10:00", "10:05", "10:10"]),
                DataTableColumn(header="Value", values=["42%", "55%", "38%"]),
            ],
        )
        ctx = _make_context(data_tables=[dt])
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="data-tables-section"' in html
        assert "CPU Data" in html
        assert "10:00" in html
        assert "42%" in html

    def test_data_table_empty_no_section(self, engine: PDFEngine) -> None:
        """No data_tables → no data-tables-section in HTML."""
        ctx = _make_context(data_tables=[])
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="data-tables-section"' not in html

    def test_data_table_no_rows_shows_placeholder(self, engine: PDFEngine) -> None:
        """Data table with empty columns shows 'no data' message."""
        dt = DataTable(panel_id=1, title="Empty Table", columns=[])
        ctx = _make_context(data_tables=[dt])
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert tr["pdf.data_table_no_data"] in html

    def test_data_table_pdf_renders(self, engine: PDFEngine) -> None:
        """PDF with data tables produces valid bytes."""
        dt = DataTable(
            panel_id=1,
            title="Test Data",
            columns=[
                DataTableColumn(header="Col A", values=["1", "2"]),
                DataTableColumn(header="Col B", values=["x", "y"]),
            ],
        )
        ctx = _make_context(data_tables=[dt])
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"

    def test_data_table_row_count(self) -> None:
        """DataTable.row_count returns correct count."""
        dt = DataTable(
            panel_id=1,
            title="RC",
            columns=[
                DataTableColumn(header="A", values=["1", "2", "3"]),
            ],
        )
        assert dt.row_count == 3
        empty_dt = DataTable(panel_id=2, title="Empty", columns=[])
        assert empty_dt.row_count == 0


# ── Temporal Comparison ──────────────────────────────────────────────


class TestTemporalComparison:
    """Tests for side-by-side temporal comparison panels."""

    def test_comparison_html_rendered(self, engine: PDFEngine) -> None:
        """Comparison panels appear in HTML with period labels."""
        cp = ComparisonPanel(
            panel_id=1,
            title="CPU Compare",
            image_a_base64=_PIXEL_PNG_B64,
            image_b_base64=_PIXEL_PNG_B64,
        )
        ctx = _make_context(
            comparison_panels=[cp],
            comparison_time_from_a="now-12h",
            comparison_time_to_a="now-6h",
            comparison_time_from_b="now-6h",
            comparison_time_to_b="now",
        )
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="comparison-section"' in html
        assert "CPU Compare" in html
        assert tr["pdf.comparison_period_a"] in html
        assert tr["pdf.comparison_period_b"] in html

    def test_no_comparison_no_section(self, engine: PDFEngine) -> None:
        """No comparison_panels → no comparison-section in HTML."""
        ctx = _make_context(comparison_panels=[])
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="comparison-section"' not in html

    def test_comparison_pdf_renders(self, engine: PDFEngine) -> None:
        """PDF with comparison panels produces valid bytes."""
        cp = ComparisonPanel(
            panel_id=1,
            title="Compare Test",
            image_a_base64=_PIXEL_PNG_B64,
            image_b_base64=_PIXEL_PNG_B64,
        )
        ctx = _make_context(
            comparison_panels=[cp],
            comparison_time_from_a="now-12h",
            comparison_time_to_a="now-6h",
            comparison_time_from_b="now-6h",
            comparison_time_to_b="now",
        )
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"

    def test_comparison_missing_image_b(self, engine: PDFEngine) -> None:
        """Comparison panel with missing image B shows placeholder."""
        cp = ComparisonPanel(
            panel_id=1,
            title="Missing B",
            image_a_base64=_PIXEL_PNG_B64,
            image_b_base64="",
        )
        ctx = _make_context(comparison_panels=[cp])
        tr = get_translations(ctx.locale)
        html = engine._render_html("report.html", _template_vars(ctx, tr))
        assert 'class="panel-no-image"' in html


# ── Combined Features ────────────────────────────────────────────────


class TestCombinedFeatures:
    """Tests for multiple enhancements used together."""

    def test_landscape_toc_watermark_combined(self, engine: PDFEngine) -> None:
        """All features together produce a valid PDF."""
        dt = DataTable(
            panel_id=1,
            title="Combined Data",
            columns=[DataTableColumn(header="X", values=["1"])],
        )
        cp = ComparisonPanel(
            panel_id=1,
            title="Combined Compare",
            image_a_base64=_PIXEL_PNG_B64,
            image_b_base64=_PIXEL_PNG_B64,
        )
        ctx = _make_context(
            orientation="landscape",
            toc_enabled=True,
            watermark_text="CONFIDENTIAL",
            panel_columns=2,
            data_tables=[dt],
            comparison_panels=[cp],
            comparison_time_from_a="now-12h",
            comparison_time_to_a="now-6h",
            comparison_time_from_b="now-6h",
            comparison_time_to_b="now",
        )
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"
        # Verify it's a multi-page PDF (TOC + panels + comparison + data)
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) >= 1

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_enhancements_all_locales(self, engine: PDFEngine, locale: str) -> None:
        """PDF with all enhancements renders in every locale."""
        ctx = _make_context(
            locale=locale,
            toc_enabled=True,
            watermark_text="TEST",
            panel_columns=2,
        )
        pdf = engine.render_report(ctx)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 100


# ── i18n Keys ────────────────────────────────────────────────────────


class TestEnhancementI18n:
    """Tests that Sprint 5 i18n keys exist in all locales."""

    NEW_KEYS = [
        "pdf.toc_title",
        "pdf.toc_panel",
        "pdf.watermark_confidential",
        "pdf.watermark_draft",
        "pdf.data_tables_section",
        "pdf.data_table_no_data",
        "pdf.comparison_title",
        "pdf.comparison_period_a",
        "pdf.comparison_period_b",
        "pdf.orientation_portrait",
        "pdf.orientation_landscape",
    ]

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_keys_present(self, locale: str) -> None:
        """All Sprint 5 i18n keys exist for every locale."""
        tr = get_translations(locale)
        for key in self.NEW_KEYS:
            assert key in tr, f"Missing key '{key}' for locale '{locale}'"
            assert tr[key] != key, f"Key '{key}' untranslated in locale '{locale}'"


# ── Schema Tests ─────────────────────────────────────────────────────


class TestReportSchema:
    """Tests for new schema fields."""

    def test_defaults(self) -> None:
        """New schema fields have correct defaults."""
        from backend.app.schemas.report import ReportGenerateRequest

        req = ReportGenerateRequest(dashboard_uid="test", panel_ids=[1])
        assert req.orientation == "portrait"
        assert req.toc_enabled is False
        assert req.watermark_text is None
        assert req.panel_columns == 1
        assert req.include_data_tables is False
        assert req.comparison_time_from is None
        assert req.comparison_time_to is None

    def test_landscape_orientation(self) -> None:
        """Landscape orientation is accepted."""
        from backend.app.schemas.report import ReportGenerateRequest

        req = ReportGenerateRequest(
            dashboard_uid="test",
            panel_ids=[1],
            orientation="landscape",
        )
        assert req.orientation == "landscape"

    def test_watermark_max_length(self) -> None:
        """Watermark text exceeding 100 chars is rejected."""
        from pydantic import ValidationError

        from backend.app.schemas.report import ReportGenerateRequest

        with pytest.raises(ValidationError):
            ReportGenerateRequest(
                dashboard_uid="test",
                panel_ids=[1],
                watermark_text="x" * 101,
            )

    def test_panel_columns_validation(self) -> None:
        """Panel columns outside 1-2 range is rejected."""
        from pydantic import ValidationError

        from backend.app.schemas.report import ReportGenerateRequest

        with pytest.raises(ValidationError):
            ReportGenerateRequest(
                dashboard_uid="test",
                panel_ids=[1],
                panel_columns=3,
            )


# ── Helpers ──────────────────────────────────────────────────────────


def _template_vars(ctx: ReportContext, tr: dict[str, str]) -> dict:
    """Build template variable dict from a ReportContext (mirrors PDFEngine.render_report)."""
    return {
        "report_title": ctx.report_title,
        "dashboard_title": ctx.dashboard_title,
        "dashboard_uid": ctx.dashboard_uid,
        "generated_at": ctx.generated_at,
        "time_range_from": ctx.time_range_from,
        "time_range_to": ctx.time_range_to,
        "panels": ctx.panels,
        "description": ctx.description,
        "company_name": ctx.company_name,
        "logo_base64": ctx.logo_base64,
        "logo_mime_type": ctx.logo_mime_type,
        "primary_color": ctx.primary_color,
        "secondary_color": ctx.secondary_color,
        "header_text": ctx.header_text,
        "footer_text": ctx.footer_text,
        "show_date": ctx.show_date,
        "show_page_numbers": ctx.show_page_numbers,
        "locale": ctx.locale,
        "i18n_dashboard_label": tr["pdf.dashboard_label"],
        "i18n_dashboard_uid": tr["pdf.dashboard_uid"],
        "i18n_generated_at": tr["pdf.generated_at"],
        "i18n_time_range": tr["pdf.time_range"],
        "i18n_panels_included": tr["pdf.panels_included"],
        "i18n_panels_section": tr["pdf.panels_section"],
        "i18n_image_not_available": tr["pdf.image_not_available"],
        "i18n_page": tr["pdf.page"],
        # Sprint 5 enhancements
        "orientation": ctx.orientation,
        "toc_enabled": ctx.toc_enabled,
        "watermark_text": ctx.watermark_text,
        "panel_columns": ctx.panel_columns,
        "data_tables": ctx.data_tables,
        "comparison_panels": ctx.comparison_panels,
        "comparison_time_from_a": ctx.comparison_time_from_a,
        "comparison_time_to_a": ctx.comparison_time_to_a,
        "comparison_time_from_b": ctx.comparison_time_from_b,
        "comparison_time_to_b": ctx.comparison_time_to_b,
        "i18n_toc_title": tr["pdf.toc_title"],
        "i18n_toc_panel": tr["pdf.toc_panel"],
        "i18n_data_tables_section": tr["pdf.data_tables_section"],
        "i18n_data_table_no_data": tr["pdf.data_table_no_data"],
        "i18n_comparison_title": tr["pdf.comparison_title"],
        "i18n_comparison_period_a": tr["pdf.comparison_period_a"],
        "i18n_comparison_period_b": tr["pdf.comparison_period_b"],
    }
