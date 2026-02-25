"""Celery tasks for PDF report generation."""

from __future__ import annotations

import base64
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from celery import shared_task  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from backend.app.services.grafana_client import GrafanaClient

logger = logging.getLogger(__name__)

# Max parallel panel renders — limited to avoid overwhelming Grafana renderer
_MAX_RENDER_WORKERS = 4


def _get_db_session() -> Session:
    """Create a standalone database session for the Celery worker.

    Returns:
        A new SQLAlchemy Session instance.
    """
    from backend.app.api.deps import get_settings
    from backend.app.core.database import get_session_factory

    settings = get_settings()
    session_factory = get_session_factory(settings)
    return session_factory()


def _get_grafana_client() -> GrafanaClient:
    """Create a GrafanaClient instance for the Celery worker.

    Returns:
        Initialized GrafanaClient.
    """
    from backend.app.api.deps import get_settings
    from backend.app.services.grafana_client import GrafanaClient

    settings = get_settings()
    return GrafanaClient(
        base_url=settings.GRAFANA_URL,
        api_key=settings.GRAFANA_API_KEY,
        timeout=settings.GRAFANA_TIMEOUT,
    )


@shared_task(
    name="generate_report",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def generate_report_task(
    self: Any,
    report_id: str,
    template_dir: str,
    request_params: dict[str, Any],
) -> dict[str, Any]:
    """Celery task that generates a PDF report and stores it in the database.

    Steps:
        1. Update report status to 'generating'
        2. Fetch dashboard details from Grafana
        3. Render each panel as PNG via Grafana render API (parallel)
        4. Build PDF context with panel images (base64-encoded)
        5. Call PDFEngine.render_report() to produce PDF bytes
        6. Store PDF bytes in report.pdf_data, update status to 'completed'
        7. On error, update status to 'failed' with error_message

    Args:
        self: Celery task instance (bound).
        report_id: UUID string of the Report record to process.
        template_dir: Path to the Jinja2 templates directory.
        request_params: Dict with width, height, time_range_from/to, template_id, language.

    Returns:
        Dict with report_id, status, and pdf_size_bytes on success.
    """
    from backend.app.models.pdf_template import PDFTemplate
    from backend.app.models.report import Report, ReportStatus
    from backend.app.services.pdf_engine import (
        ComparisonPanel,
        PanelImage,
        PDFEngine,
        ReportContext,
    )

    report_uuid = uuid.UUID(report_id)
    db = _get_db_session()
    grafana_client = _get_grafana_client()

    try:
        report_obj = db.query(Report).filter(Report.id == report_uuid).first()
        if report_obj is None:
            logger.error("Report %s not found in Celery task", report_id)
            return {"report_id": report_id, "status": "not_found"}

        report: Report = report_obj
        report.status = ReportStatus.GENERATING.value
        db.commit()

        logger.info(
            "Generating report %s for dashboard %s (task_id=%s)",
            report_id,
            report.dashboard_uid,
            self.request.id,
        )

        # Fetch panel images from Grafana — in parallel for speed
        panel_images: list[PanelImage] = []
        dashboard_data = grafana_client.get_dashboard(report.dashboard_uid)
        dashboard_panels = dashboard_data.get("dashboard", {}).get("panels", [])

        # Build a lookup for panel titles
        panel_title_map = {
            p["id"]: p.get("title", f"Panel {p['id']}") for p in dashboard_panels
        }

        render_width = request_params.get("width", 1000)
        render_height = request_params.get("height", 500)
        time_from = report.time_range_from or "now-6h"
        time_to = report.time_range_to or "now"

        def _render_single(pid: int) -> PanelImage:
            """Render one panel, returning a PanelImage."""
            try:
                png_bytes = grafana_client.render_panel(
                    dashboard_uid=report.dashboard_uid,
                    panel_id=pid,
                    width=render_width,
                    height=render_height,
                    from_time=time_from,
                    to_time=time_to,
                )
                image_b64 = base64.b64encode(png_bytes).decode("utf-8")
                return PanelImage(
                    panel_id=pid,
                    title=panel_title_map.get(pid, f"Panel {pid}"),
                    image_base64=image_b64,
                )
            except Exception as exc:
                logger.warning("Failed to render panel %d: %s", pid, exc)
                return PanelImage(
                    panel_id=pid,
                    title=panel_title_map.get(pid, f"Panel {pid}"),
                    image_base64="",
                )

        # Parallel render with ThreadPoolExecutor
        workers = min(_MAX_RENDER_WORKERS, len(report.panel_ids))
        results_map: dict[int, PanelImage] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_pid = {
                executor.submit(_render_single, pid): pid for pid in report.panel_ids
            }
            for future in as_completed(future_to_pid):
                pid = future_to_pid[future]
                results_map[pid] = future.result()

        # Preserve original panel order
        panel_images = [results_map[pid] for pid in report.panel_ids if pid in results_map]

        logger.info(
            "Rendered %d/%d panels in parallel for report %s",
            len(panel_images),
            len(report.panel_ids),
            report_id,
        )

        # Load template branding if template_id provided
        template_id = request_params.get("template_id")
        tpl_kwargs: dict = {}
        base_pdf_bytes: bytes | None = None
        if template_id:
            tpl = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
            if tpl:
                tpl_kwargs = {
                    "company_name": tpl.company_name or "",
                    "logo_base64": tpl.logo_base64,
                    "logo_mime_type": tpl.logo_mime_type,
                    "primary_color": tpl.primary_color,
                    "secondary_color": tpl.secondary_color,
                    "header_text": tpl.header_text,
                    "footer_text": tpl.footer_text,
                    "show_date": tpl.show_date,
                    "show_page_numbers": tpl.show_page_numbers,
                }
                if tpl.base_pdf_data:
                    base_pdf_bytes = tpl.base_pdf_data

        # Build PDF context
        locale = request_params.get("language", "ca")
        orientation = request_params.get("orientation", "portrait")
        toc_enabled = request_params.get("toc_enabled", False)
        watermark_text = request_params.get("watermark_text")
        panel_columns = request_params.get("panel_columns", 1)

        # --- Temporal comparison ---
        comparison_panels: list[ComparisonPanel] = []
        comparison_time_from = request_params.get("comparison_time_from")
        comparison_time_to = request_params.get("comparison_time_to")
        if comparison_time_from and comparison_time_to:
            # Render panels for period B (period A is already in panel_images)
            def _render_comparison(pid: int) -> ComparisonPanel:
                """Render a panel for both time periods."""
                # Image A is from the main panel_images
                img_a = results_map.get(pid)
                img_a_b64 = img_a.image_base64 if img_a else ""
                try:
                    png_b = grafana_client.render_panel(
                        dashboard_uid=report.dashboard_uid,
                        panel_id=pid,
                        width=render_width,
                        height=render_height,
                        from_time=comparison_time_from,
                        to_time=comparison_time_to,
                    )
                    img_b_b64 = base64.b64encode(png_b).decode("utf-8")
                except Exception as exc:
                    logger.warning("Failed to render comparison panel %d: %s", pid, exc)
                    img_b_b64 = ""
                return ComparisonPanel(
                    panel_id=pid,
                    title=panel_title_map.get(pid, f"Panel {pid}"),
                    image_a_base64=img_a_b64,
                    image_b_base64=img_b_b64,
                )

            comp_workers = min(_MAX_RENDER_WORKERS, len(report.panel_ids))
            with ThreadPoolExecutor(max_workers=comp_workers) as executor:
                comp_future_map = {
                    executor.submit(_render_comparison, pid): pid
                    for pid in report.panel_ids
                }
                comp_results: dict[int, ComparisonPanel] = {}
                for comp_future in as_completed(comp_future_map):
                    pid = comp_future_map[comp_future]
                    comp_results[pid] = comp_future.result()
            comparison_panels = [
                comp_results[pid] for pid in report.panel_ids if pid in comp_results
            ]
            logger.info("Rendered %d comparison panels", len(comparison_panels))

        context = ReportContext(
            report_title=report.title,
            dashboard_title=report.dashboard_title,
            dashboard_uid=report.dashboard_uid,
            generated_at=datetime.now(UTC).isoformat(),
            time_range_from=report.time_range_from or "now-6h",
            time_range_to=report.time_range_to or "now",
            panels=panel_images,
            description=report.description,
            locale=locale,
            orientation=orientation,
            toc_enabled=toc_enabled,
            watermark_text=watermark_text,
            panel_columns=panel_columns,
            comparison_panels=comparison_panels,
            comparison_time_from_a=report.time_range_from or "now-6h",
            comparison_time_to_a=report.time_range_to or "now",
            comparison_time_from_b=comparison_time_from,
            comparison_time_to_b=comparison_time_to,
            **tpl_kwargs,
        )

        # Generate PDF
        pdf_engine = PDFEngine(template_dir=template_dir)
        pdf_bytes = pdf_engine.render_report(context)

        # If a base PDF template is set, overlay the generated pages onto it
        if base_pdf_bytes:
            pdf_bytes = pdf_engine.overlay_on_base_pdf(base_pdf_bytes, pdf_bytes)

        # Store PDF in database
        report.pdf_data = pdf_bytes
        report.pdf_size_bytes = len(pdf_bytes)
        report.status = ReportStatus.COMPLETED.value
        report.generated_at = datetime.now(UTC)
        db.commit()

        logger.info(
            "Report %s generated successfully (%d bytes, task_id=%s)",
            report_id,
            len(pdf_bytes),
            self.request.id,
        )

        return {
            "report_id": report_id,
            "status": "completed",
            "pdf_size_bytes": len(pdf_bytes),
        }

    except Exception as e:
        logger.error(
            "Report generation failed for %s: %s (task_id=%s)",
            report_id,
            e,
            self.request.id,
            exc_info=True,
        )
        try:
            failed_report = db.query(Report).filter(Report.id == report_uuid).first()
            if failed_report:
                failed_report.status = ReportStatus.FAILED.value
                failed_report.error_message = str(e)
                db.commit()
        except Exception:
            logger.error("Failed to update report status to failed", exc_info=True)

        return {"report_id": report_id, "status": "failed", "error": str(e)}

    finally:
        grafana_client.close()
        db.close()
