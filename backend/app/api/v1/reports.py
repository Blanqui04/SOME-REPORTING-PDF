"""Report API endpoints."""

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, get_grafana_client, get_settings
from backend.app.core.config import Settings
from backend.app.models.user import User
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.report import BatchGenerateRequest, ReportGenerateRequest, ReportResponse
from backend.app.services.grafana_client import GrafanaClient
from backend.app.services.report_service import ReportService, calculate_pages
from backend.app.tasks.report_tasks import generate_report_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_report(
    request: ReportGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportResponse:
    """Trigger PDF report generation via Celery background task.

    Creates a report record with status 'pending' and enqueues
    the PDF generation as a Celery task.

    Args:
        request: Report generation parameters.
        current_user: Authenticated user.
        db: Database session.
        grafana: Grafana API client.
        settings: Application settings.

    Returns:
        Report metadata with status 'pending'.
    """
    # Fetch dashboard title from Grafana
    dashboard_data = grafana.get_dashboard(request.dashboard_uid)
    dashboard_title = dashboard_data.get("dashboard", {}).get("title", "Unknown Dashboard")

    service = ReportService(db)
    report = service.create_report(
        user_id=current_user.id,
        request=request,
        dashboard_title=dashboard_title,
    )

    # Get template directory path
    template_dir = str(Path(__file__).resolve().parents[2] / "templates")

    # Enqueue Celery task for PDF generation
    generate_report_task.delay(
        report_id=str(report.id),
        template_dir=template_dir,
        request_params={
            "width": request.width,
            "height": request.height,
            "template_id": request.template_id,
            "language": request.language,
            "orientation": request.orientation,
            "toc_enabled": request.toc_enabled,
            "watermark_text": request.watermark_text,
            "panel_columns": request.panel_columns,
            "include_data_tables": request.include_data_tables,
            "comparison_time_from": request.comparison_time_from,
            "comparison_time_to": request.comparison_time_to,
        },
    )

    return ReportResponse.model_validate(report)


@router.get("/stats")
def get_report_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Get report generation statistics for the current user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Statistics including total count, by-status breakdown,
        total/avg PDF size, and top dashboards.
    """
    service = ReportService(db)
    return service.get_stats(user_id=current_user.id)


@router.get("", response_model=PaginatedResponse[ReportResponse])
def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> PaginatedResponse[ReportResponse]:
    """List reports for the current user with pagination.

    Args:
        current_user: Authenticated user.
        db: Database session.
        page: Page number (1-indexed).
        per_page: Number of items per page (1-100).
        status_filter: Optional filter by report status.

    Returns:
        Paginated list of report metadata.
    """
    service = ReportService(db)
    reports, total = service.list_reports(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        status_filter=status_filter,
    )

    return PaginatedResponse[ReportResponse](
        items=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        page=page,
        per_page=per_page,
        pages=calculate_pages(total, per_page),
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReportResponse:
    """Get a single report's metadata by ID.

    Args:
        report_id: Report UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Report metadata.
    """
    service = ReportService(db)
    report = service.get_report(user_id=current_user.id, report_id=report_id)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Download the generated PDF file.

    Args:
        report_id: Report UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        PDF file as HTTP response with Content-Disposition header.
    """
    service = ReportService(db)
    report = service.get_report_for_download(user_id=current_user.id, report_id=report_id)

    return Response(
        content=report.pdf_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report.file_name}"',
        },
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a report by ID.

    Args:
        report_id: Report UUID.
        current_user: Authenticated user.
        db: Database session.
    """
    service = ReportService(db)
    service.delete_report(user_id=current_user.id, report_id=report_id)


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
def batch_generate(
    request: BatchGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, list[ReportResponse]]:
    """Generate PDF reports for multiple dashboards in one request.

    Creates a separate report record and Celery task for each
    dashboard UID provided.

    Args:
        request: Batch generation parameters with list of dashboard UIDs.
        current_user: Authenticated user.
        db: Database session.
        grafana: Grafana API client.
        settings: Application settings.

    Returns:
        Dictionary with list of created report responses.
    """
    service = ReportService(db)
    template_dir = str(Path(__file__).resolve().parents[2] / "templates")
    reports: list[ReportResponse] = []

    for dashboard_uid in request.dashboard_uids:
        try:
            dashboard_data = grafana.get_dashboard(dashboard_uid)
            dashboard_title = dashboard_data.get("dashboard", {}).get("title", "Unknown")

            # Get panel IDs from request or dashboard
            panel_ids = request.panel_ids
            if not panel_ids:
                panels = dashboard_data.get("dashboard", {}).get("panels", [])
                panel_ids = [p["id"] for p in panels if "id" in p]

            gen_request = ReportGenerateRequest(
                dashboard_uid=dashboard_uid,
                panel_ids=panel_ids,
                time_range_from=request.time_range_from,
                time_range_to=request.time_range_to,
                width=request.width,
                height=request.height,
                language=request.language,
                orientation=request.orientation,
            )

            report = service.create_report(
                user_id=current_user.id,
                request=gen_request,
                dashboard_title=dashboard_title,
            )

            generate_report_task.delay(
                report_id=str(report.id),
                template_dir=template_dir,
                request_params={
                    "width": request.width,
                    "height": request.height,
                    "language": request.language,
                    "orientation": request.orientation,
                },
            )

            reports.append(ReportResponse.model_validate(report))
            logger.info("Batch: queued report for dashboard %s", dashboard_uid)
        except Exception as exc:
            logger.error("Batch: failed for dashboard %s: %s", dashboard_uid, exc)

    return {"reports": reports}
