"""Report CRUD service and background generation orchestration."""

import logging
import math
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError, ReportNotReadyError
from backend.app.models.report import Report, ReportStatus
from backend.app.schemas.report import ReportGenerateRequest

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

    def delete_report(self, user_id: uuid.UUID, report_id: uuid.UUID) -> None:
        """Delete a report owned by the user.

        Args:
            user_id: The current user's UUID.
            report_id: The report's UUID.

        Raises:
            NotFoundError: If report not found or not owned by user.
        """
        report = self.get_report(user_id, report_id)
        self._db.delete(report)
        self._db.commit()
        logger.info("Report deleted: %s", report_id)

    def get_stats(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Get report generation statistics for a user.

        Args:
            user_id: The current user's UUID.

        Returns:
            Dict with total, by_status counts, total_size_bytes,
            avg_size_bytes, and top_dashboards.
        """
        base = self._db.query(Report).filter(Report.created_by_id == user_id)

        total = base.count()

        # Count by status
        status_rows = (
            base.with_entities(Report.status, func.count(Report.id))
            .group_by(Report.status)
            .all()
        )
        by_status: dict[str, int] = {s.value: 0 for s in ReportStatus}
        for status_val, cnt in status_rows:
            by_status[status_val] = cnt

        # Total and average PDF size
        size_agg = base.filter(Report.pdf_size_bytes.isnot(None)).with_entities(
            func.coalesce(func.sum(Report.pdf_size_bytes), 0),
            func.coalesce(func.avg(Report.pdf_size_bytes), 0),
        ).first()
        total_size = int(size_agg[0]) if size_agg else 0
        avg_size = int(size_agg[1]) if size_agg else 0

        # Top dashboards (by report count)
        top_rows = (
            base.with_entities(
                Report.dashboard_uid,
                Report.dashboard_title,
                func.count(Report.id).label("count"),
            )
            .group_by(Report.dashboard_uid, Report.dashboard_title)
            .order_by(func.count(Report.id).desc())
            .limit(5)
            .all()
        )
        top_dashboards = [
            {"uid": uid, "title": title, "count": cnt}
            for uid, title, cnt in top_rows
        ]

        return {
            "total": total,
            "by_status": by_status,
            "total_size_bytes": total_size,
            "avg_size_bytes": avg_size,
            "top_dashboards": top_dashboards,
        }


def calculate_pages(total: int, per_page: int) -> int:
    """Calculate total number of pages for pagination.

    Args:
        total: Total number of items.
        per_page: Items per page.

    Returns:
        Total number of pages.
    """
    return max(1, math.ceil(total / per_page))
