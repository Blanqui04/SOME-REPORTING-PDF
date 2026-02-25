"""Audit log service for recording user actions."""

import logging
import uuid

from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Records user actions in the audit log.

    Args:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        user_id: uuid.UUID | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata_json: dict | None = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            action: Action performed (e.g. 'create', 'delete', 'login').
            resource_type: Type of resource (e.g. 'report', 'schedule', 'user').
            resource_id: UUID string of the affected resource.
            user_id: UUID of the user who performed the action.
            details: Human-readable description of the action.
            ip_address: Client IP address.
            user_agent: Client User-Agent header.
            metadata_json: Additional structured data.

        Returns:
            The created AuditLog ORM instance.
        """
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata_json,
        )
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)

        logger.info(
            "Audit: user=%s action=%s resource=%s/%s",
            user_id,
            action,
            resource_type,
            resource_id,
        )
        return entry

    def list_logs(
        self,
        page: int = 1,
        per_page: int = 50,
        action: str | None = None,
        resource_type: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[AuditLog], int]:
        """List audit log entries with optional filters.

        Args:
            page: Page number (1-indexed).
            per_page: Number of items per page.
            action: Filter by action type.
            resource_type: Filter by resource type.
            user_id: Filter by user ID.

        Returns:
            Tuple of (audit log entries, total count).
        """
        query = self._db.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        total = query.count()
        entries = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return entries, total
