"""PDF rendering engine using Jinja2 and WeasyPrint."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from weasyprint import HTML

from backend.app.core.exceptions import PDFRenderError

logger = logging.getLogger(__name__)


@dataclass
class PanelImage:
    """Represents a rendered panel image for PDF inclusion.

    Attributes:
        panel_id: Grafana panel ID.
        title: Panel display title.
        image_base64: Base64-encoded PNG image data.
    """

    panel_id: int
    title: str
    image_base64: str


@dataclass
class ReportContext:
    """All data needed to render a PDF report.

    Attributes:
        report_title: Main title displayed on the report.
        dashboard_title: Grafana dashboard title.
        dashboard_uid: Grafana dashboard UID.
        generated_at: ISO formatted generation timestamp.
        time_range_from: Time range start (Grafana format).
        time_range_to: Time range end (Grafana format).
        panels: List of panel images to include.
        description: Optional report description.
        company_name: Company name displayed in header/footer.
    """

    report_title: str
    dashboard_title: str
    dashboard_uid: str
    generated_at: str
    time_range_from: str
    time_range_to: str
    panels: list[PanelImage] = field(default_factory=list)
    description: str | None = None
    company_name: str = "SOME S.A.U."


class PDFEngine:
    """Renders HTML templates to PDF using Jinja2 and WeasyPrint.

    The engine loads Jinja2 templates from the templates directory,
    injects report data, and converts the resulting HTML to PDF bytes.

    Args:
        template_dir: Absolute path to the templates/ directory.
    """

    def __init__(self, template_dir: str | Path) -> None:
        self._template_dir = Path(template_dir)
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=True,
        )

    def render_report(self, context: ReportContext) -> bytes:
        """Render a complete PDF report from the given context.

        Args:
            context: All data needed for the report template.

        Returns:
            Raw PDF bytes.

        Raises:
            PDFRenderError: If template rendering or PDF conversion fails.
        """
        logger.info(
            "Rendering PDF for '%s' (%d panels)",
            context.report_title,
            len(context.panels),
        )

        template_vars = {
            "report_title": context.report_title,
            "dashboard_title": context.dashboard_title,
            "dashboard_uid": context.dashboard_uid,
            "generated_at": context.generated_at,
            "time_range_from": context.time_range_from,
            "time_range_to": context.time_range_to,
            "panels": context.panels,
            "description": context.description,
            "company_name": context.company_name,
        }

        html_content = self._render_html("report.html", template_vars)
        pdf_bytes = self._html_to_pdf(html_content)

        logger.info("PDF rendered successfully (%d bytes)", len(pdf_bytes))
        return pdf_bytes

    def _render_html(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 template to an HTML string.

        Args:
            template_name: Name of the template file (e.g. 'report.html').
            context: Template variable dict.

        Returns:
            Rendered HTML string.

        Raises:
            PDFRenderError: If template is not found or rendering fails.
        """
        try:
            template = self._env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound as e:
            raise PDFRenderError(f"Template '{template_name}' not found") from e
        except Exception as e:
            raise PDFRenderError(f"Template rendering error: {e}") from e

    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert an HTML string to PDF bytes using WeasyPrint.

        Args:
            html_content: Complete HTML document string.

        Returns:
            Raw PDF file bytes.

        Raises:
            PDFRenderError: If WeasyPrint conversion fails.
        """
        try:
            html = HTML(
                string=html_content,
                base_url=str(self._template_dir),
            )
            return html.write_pdf()
        except Exception as e:
            raise PDFRenderError(f"WeasyPrint conversion error: {e}") from e
