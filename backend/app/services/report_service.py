"""Report CRUD service and background generation orchestration."""

import base64
import logging
import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.exceptions import NotFoundError, ReportNotReadyError
from backend.app.models.report import Report, ReportStatus
from backend.app.schemas.report import ReportGenerateRequest
from backend.app.services.grafana_client import GrafanaClient

logger = logging.getLogger(__name__)


class ReportService:
    """Orchestrates report creation, listing, and retrieval.

    Args:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_report(
        self, user_id: uuid.UUID, request: ReportGenerateRequest, dashboard_title: str
    ) -> Report:
        """Create a new Report record with status=pending.

        Args:
            user_id: The ID of the requesting user.
            request: Validated report generation parameters.
            dashboard_title: Title of the Grafana dashboard.

        Returns:
            The newly created Report ORM instance.
        """
        title = request.title or f"Report - {dashboard_title}"
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        file_name = f"report_{request.dashboard_uid}_{timestamp}.pdf"

        report = Report(
            title=title,
            description=request.description,
            dashboard_uid=request.dashboard_uid,
            dashboard_title=dashboard_title,
            panel_ids=request.panel_ids,
            time_range_from=request.time_range_from,
            time_range_to=request.time_range_to,
            status=ReportStatus.PENDING.value,
            file_name=file_name,
            created_by_id=user_id,
        )
        self._db.add(report)
        self._db.commit()
        self._db.refresh(report)

        logger.info("Report created: %s (id=%s)", report.title, report.id)
        return report

    def get_report(self, user_id: uuid.UUID, report_id: uuid.UUID) -> Report:
        """Fetch a single report belonging to the user.

        Args:
            user_id: The current user's UUID.
            report_id: The report's UUID.

        Returns:
            The Report ORM instance.

        Raises:
            NotFoundError: If report does not exist or is not owned by user.
        """
        report = (
            self._db.query(Report)
            .filter(Report.id == report_id, Report.created_by_id == user_id)
            .first()
        )
        if report is None:
            raise NotFoundError("Report", str(report_id))
        return report

    def list_reports(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        status_filter: str | None = None,
    ) -> tuple[list[Report], int]:
        """List paginated reports for a user.

        Args:
            user_id: The current user's UUID.
            page: Page number (1-indexed).
            per_page: Number of items per page.
            status_filter: Optional status to filter by.

        Returns:
            Tuple of (report list, total count).
        """
        query = self._db.query(Report).filter(Report.created_by_id == user_id)

        if status_filter:
            query = query.filter(Report.status == status_filter)

        total = query.count()
        reports = (
            query.order_by(Report.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return reports, total

    def get_report_for_download(self, user_id: uuid.UUID, report_id: uuid.UUID) -> Report:
        """Fetch report with PDF data for download.

        Args:
            user_id: The current user's UUID.
            report_id: The report's UUID.

        Returns:
            The Report ORM instance with pdf_data loaded.

        Raises:
            NotFoundError: If report not found or not owned by user.
            ReportNotReadyError: If status is not 'completed'.
        """
        report = self.get_report(user_id, report_id)

        if report.status != ReportStatus.COMPLETED.value:
            raise ReportNotReadyError(str(report_id), report.status)

        return report


def generate_report_task(
    report_id: uuid.UUID,
    grafana_client: GrafanaClient,
    session_factory: sessionmaker,  # type: ignore[type-arg]
    template_dir: str,
    request_params: dict,
) -> None:
    """Background task that generates PDF and stores it in the database.

    This function runs outside the request lifecycle, so it creates
    its own database session. Steps:
        1. Update report status to 'generating'
        2. Fetch dashboard details from Grafana
        3. Render each panel as PNG via Grafana render API
        4. Build PDF context with panel images (base64-encoded)
        5. Call PDFEngine.render_report() to produce PDF bytes
        6. Store PDF bytes in report.pdf_data, update status to 'completed'
        7. On error, update status to 'failed' with error_message

    Args:
        report_id: UUID of the Report record to process.
        grafana_client: Initialized GrafanaClient instance.
        session_factory: SQLAlchemy sessionmaker for creating a new session.
        template_dir: Path to the Jinja2 templates directory.
        request_params: Dict with width, height, time_range_from, time_range_to.
    """
    from backend.app.services.pdf_engine import PanelImage, PDFEngine, ReportContext

    db = session_factory()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report is None:
            logger.error("Report %s not found in background task", report_id)
            return

        report.status = ReportStatus.GENERATING.value
        db.commit()

        logger.info("Generating report %s for dashboard %s", report_id, report.dashboard_uid)

        # Fetch panel images from Grafana
        panel_images: list[PanelImage] = []
        dashboard_data = grafana_client.get_dashboard(report.dashboard_uid)
        dashboard_panels = dashboard_data.get("dashboard", {}).get("panels", [])

        # Build a lookup for panel titles
        panel_title_map = {p["id"]: p.get("title", f"Panel {p['id']}") for p in dashboard_panels}

        for panel_id in report.panel_ids:
            try:
                png_bytes = grafana_client.render_panel(
                    dashboard_uid=report.dashboard_uid,
                    panel_id=panel_id,
                    width=request_params.get("width", 1000),
                    height=request_params.get("height", 500),
                    from_time=report.time_range_from or "now-6h",
                    to_time=report.time_range_to or "now",
                )
                image_b64 = base64.b64encode(png_bytes).decode("utf-8")
                panel_images.append(
                    PanelImage(
                        panel_id=panel_id,
                        title=panel_title_map.get(panel_id, f"Panel {panel_id}"),
                        image_base64=image_b64,
                    )
                )
            except Exception as e:
                logger.warning("Failed to render panel %d: %s", panel_id, e)
                panel_images.append(
                    PanelImage(
                        panel_id=panel_id,
                        title=panel_title_map.get(panel_id, f"Panel {panel_id}"),
                        image_base64="",
                    )
                )

        # Build PDF context
        context = ReportContext(
            report_title=report.title,
            dashboard_title=report.dashboard_title,
            dashboard_uid=report.dashboard_uid,
            generated_at=datetime.now(UTC).isoformat(),
            time_range_from=report.time_range_from or "now-6h",
            time_range_to=report.time_range_to or "now",
            panels=panel_images,
            description=report.description,
        )

        # Generate PDF
        pdf_engine = PDFEngine(template_dir=template_dir)
        pdf_bytes = pdf_engine.render_report(context)

        # Store PDF in database
        report.pdf_data = pdf_bytes
        report.pdf_size_bytes = len(pdf_bytes)
        report.status = ReportStatus.COMPLETED.value
        report.generated_at = datetime.now(UTC)
        db.commit()

        logger.info(
            "Report %s generated successfully (%d bytes)",
            report_id,
            len(pdf_bytes),
        )

    except Exception as e:
        logger.error("Report generation failed for %s: %s", report_id, e, exc_info=True)
        try:
            report = db.query(Report).filter(Report.id == report_id).first()
            if report:
                report.status = ReportStatus.FAILED.value
                report.error_message = str(e)
                db.commit()
        except Exception:
            logger.error("Failed to update report status to failed", exc_info=True)
    finally:
        db.close()


def calculate_pages(total: int, per_page: int) -> int:
    """Calculate total number of pages for pagination.

    Args:
        total: Total number of items.
        per_page: Items per page.

    Returns:
        Total number of pages.
    """
    return max(1, math.ceil(total / per_page))
