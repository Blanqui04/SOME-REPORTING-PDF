"""Schedule API endpoints for managing recurring report generation."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, get_grafana_client
from backend.app.models.user import User
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from backend.app.services.grafana_client import GrafanaClient
from backend.app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _calculate_pages(total: int, per_page: int) -> int:
    """Calculate total pages for pagination."""
    import math

    return max(1, math.ceil(total / per_page))


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    request: ScheduleCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
) -> ScheduleResponse:
    """Create a new scheduled report.

    Args:
        request: Schedule creation parameters.
        current_user: Authenticated user.
        db: Database session.
        grafana: Grafana API client (for dashboard title lookup).

    Returns:
        Created schedule metadata.
    """
    # Fetch dashboard title from Grafana
    dashboard_data = grafana.get_dashboard(request.dashboard_uid)
    dashboard_title = dashboard_data.get("dashboard", {}).get("title", "Unknown Dashboard")

    service = ScheduleService(db)
    schedule = service.create_schedule(
        user_id=current_user.id,
        request=request,
        dashboard_title=dashboard_title,
    )

    return ScheduleResponse.model_validate(schedule)


@router.get("", response_model=PaginatedResponse[ScheduleResponse])
def list_schedules(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    active_only: bool = Query(default=False),
) -> PaginatedResponse[ScheduleResponse]:
    """List schedules for the current user with pagination.

    Args:
        current_user: Authenticated user.
        db: Database session.
        page: Page number (1-indexed).
        per_page: Number of items per page.
        active_only: If true, return only active schedules.

    Returns:
        Paginated list of schedule metadata.
    """
    service = ScheduleService(db)
    schedules, total = service.list_schedules(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        active_only=active_only,
    )

    return PaginatedResponse[ScheduleResponse](
        items=[ScheduleResponse.model_validate(s) for s in schedules],
        total=total,
        page=page,
        per_page=per_page,
        pages=_calculate_pages(total, per_page),
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ScheduleResponse:
    """Get a single schedule by ID.

    Args:
        schedule_id: Schedule UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Schedule metadata.
    """
    service = ScheduleService(db)
    schedule = service.get_schedule(user_id=current_user.id, schedule_id=schedule_id)
    return ScheduleResponse.model_validate(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: uuid.UUID,
    request: ScheduleUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ScheduleResponse:
    """Update a schedule by ID.

    Args:
        schedule_id: Schedule UUID.
        request: Update parameters.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated schedule metadata.
    """
    service = ScheduleService(db)
    schedule = service.update_schedule(
        user_id=current_user.id,
        schedule_id=schedule_id,
        request=request,
    )
    return ScheduleResponse.model_validate(schedule)


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
def toggle_schedule(
    schedule_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ScheduleResponse:
    """Toggle a schedule's active state.

    Args:
        schedule_id: Schedule UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated schedule metadata.
    """
    service = ScheduleService(db)
    schedule = service.toggle_schedule(
        user_id=current_user.id,
        schedule_id=schedule_id,
    )
    return ScheduleResponse.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a schedule by ID.

    Args:
        schedule_id: Schedule UUID.
        current_user: Authenticated user.
        db: Database session.
    """
    service = ScheduleService(db)
    service.delete_schedule(user_id=current_user.id, schedule_id=schedule_id)
