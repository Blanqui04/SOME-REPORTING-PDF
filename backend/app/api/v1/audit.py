"""Audit log API endpoints (admin-only)."""

import logging
import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.permissions import require_admin
from backend.app.models.user import User
from backend.app.schemas.audit import AuditLogResponse
from backend.app.schemas.common import PaginatedResponse
from backend.app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    user_id: uuid.UUID | None = None,
) -> PaginatedResponse[AuditLogResponse]:
    """List audit log entries (admin only).

    Args:
        _admin: Authenticated admin user.
        db: Database session.
        page: Page number (1-indexed).
        per_page: Items per page.
        action: Optional filter by action type.
        resource_type: Optional filter by resource type.
        user_id: Optional filter by user ID.

    Returns:
        Paginated list of audit log entries.
    """
    service = AuditService(db)
    entries, total = service.list_logs(
        page=page,
        per_page=per_page,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
    )

    return PaginatedResponse[AuditLogResponse](
        items=[AuditLogResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, math.ceil(total / per_page)),
    )
