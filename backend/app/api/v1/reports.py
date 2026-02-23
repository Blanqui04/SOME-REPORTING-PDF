"""Report API endpoints."""

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, get_grafana_client, get_settings
from backend.app.core.config import Settings
from backend.app.core.database import get_session_factory
from backend.app.models.user import User
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.report import ReportGenerateRequest, ReportResponse
from backend.app.services.grafana_client import GrafanaClient
from backend.app.services.report_service import (
    ReportService,
    calculate_pages,
    generate_report_task,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportResponse:
    """Trigger PDF report generation in the background.

    Creates a report record with status 'pending' and enqueues
    the PDF generation as a background task.

    Args:
        request: Report generation parameters.
        background_tasks: FastAPI background task scheduler.
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

    # Enqueue background PDF generation
    session_factory = get_session_factory(settings)
    background_tasks.add_task(
        generate_report_task,
        report_id=report.id,
        grafana_client=grafana,
        session_factory=session_factory,
        template_dir=template_dir,
        request_params={
            "width": request.width,
            "height": request.height,
        },
    )

    return ReportResponse.model_validate(report)


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
