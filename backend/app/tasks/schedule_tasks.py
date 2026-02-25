"""Celery tasks for schedule-based report generation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from celery import shared_task  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@shared_task(name="execute_due_schedules")
def execute_due_schedules() -> dict[str, Any]:
    """Periodic task that finds and executes all due schedules.

    This task is meant to be called by Celery Beat every minute.
    It queries for active schedules whose next_run_at is in the past,
    then enqueues a report generation task for each one.

    Returns:
        Dict with count of executed schedules.
    """
    # Import here to avoid circular imports
    from backend.app.api.deps import get_settings
    from backend.app.core.database import get_session_factory
    from backend.app.services.schedule_service import ScheduleService
    from backend.app.tasks.report_tasks import generate_report_task

    settings = get_settings()
    session_factory = get_session_factory(settings)
    db = session_factory()

    try:
        service = ScheduleService(db)
        due_schedules = service.get_due_schedules()

        if not due_schedules:
            return {"executed": 0}

        template_dir = str(Path(__file__).resolve().parents[1] / "templates")
        executed = 0

        for schedule in due_schedules:
            try:
                # Enqueue the report generation task
                generate_report_task.delay(
                    report_id=_create_scheduled_report(db, schedule),
                    template_dir=template_dir,
                    request_params={
                        "width": schedule.width,
                        "height": schedule.height,
                        "template_id": schedule.template_id,
                        "language": schedule.language,
                        "schedule_id": str(schedule.id),
                        "email_recipients": schedule.email_recipients,
                        "webhook_url": schedule.webhook_url,
                    },
                )

                service.mark_schedule_run(schedule)
                executed += 1

                logger.info(
                    "Enqueued report for schedule %s (%s)",
                    schedule.id,
                    schedule.name,
                )
            except Exception as e:
                logger.error(
                    "Failed to enqueue schedule %s: %s",
                    schedule.id,
                    e,
                    exc_info=True,
                )

        logger.info("Executed %d due schedules", executed)
        return {"executed": executed}

    finally:
        db.close()


def _create_scheduled_report(db: Any, schedule: Any) -> str:
    """Create a Report record for a scheduled run.

    Args:
        db: SQLAlchemy database session.
        schedule: Schedule ORM instance.

    Returns:
        String UUID of the created Report.
    """
    from datetime import UTC, datetime

    from backend.app.models.report import Report, ReportStatus

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    file_name = f"scheduled_{schedule.dashboard_uid}_{timestamp}.pdf"

    report = Report(
        title=f"[Scheduled] {schedule.name}",
        description=schedule.description,
        dashboard_uid=schedule.dashboard_uid,
        dashboard_title=schedule.dashboard_title or "Unknown Dashboard",
        panel_ids=schedule.panel_ids,
        time_range_from=schedule.time_range_from,
        time_range_to=schedule.time_range_to,
        status=ReportStatus.PENDING.value,
        file_name=file_name,
        created_by_id=schedule.user_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return str(report.id)
