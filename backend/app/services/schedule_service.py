"""Schedule CRUD service for managing recurring report jobs."""

import logging
import uuid
from datetime import UTC, datetime

from croniter import croniter
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.schedule import Schedule
from backend.app.schemas.schedule import ScheduleCreateRequest, ScheduleUpdateRequest

logger = logging.getLogger(__name__)


class ScheduleService:
    """Manages CRUD operations for scheduled report generation.

    Args:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_schedule(
        self, user_id: uuid.UUID, request: ScheduleCreateRequest, dashboard_title: str | None = None
    ) -> Schedule:
        """Create a new schedule record.

        Args:
            user_id: The ID of the requesting user.
            request: Validated schedule creation parameters.
            dashboard_title: Title of the Grafana dashboard.

        Returns:
            The newly created Schedule ORM instance.
        """
        next_run = self._calculate_next_run(request.cron_expression)

        schedule = Schedule(
            name=request.name,
            dashboard_uid=request.dashboard_uid,
            panel_ids=request.panel_ids,
            cron_expression=request.cron_expression,
            time_range_from=request.time_range_from,
            time_range_to=request.time_range_to,
            email_recipients=request.email_recipients,
            webhook_url=request.webhook_url,
            language=request.language,
            template_id=request.template_id,
            width=request.width,
            height=request.height,
            description=request.description,
            dashboard_title=dashboard_title,
            is_active=True,
            user_id=user_id,
            next_run_at=next_run,
        )
        self._db.add(schedule)
        self._db.commit()
        self._db.refresh(schedule)

        logger.info("Schedule created: %s (id=%s)", schedule.name, schedule.id)
        return schedule

    def get_schedule(self, user_id: uuid.UUID, schedule_id: uuid.UUID) -> Schedule:
        """Fetch a single schedule belonging to the user.

        Args:
            user_id: The current user's UUID.
            schedule_id: The schedule's UUID.

        Returns:
            The Schedule ORM instance.

        Raises:
            NotFoundError: If schedule does not exist or is not owned by user.
        """
        schedule = (
            self._db.query(Schedule)
            .filter(Schedule.id == schedule_id, Schedule.user_id == user_id)
            .first()
        )
        if schedule is None:
            raise NotFoundError("Schedule", str(schedule_id))
        return schedule

    def list_schedules(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        active_only: bool = False,
    ) -> tuple[list[Schedule], int]:
        """List paginated schedules for a user.

        Args:
            user_id: The current user's UUID.
            page: Page number (1-indexed).
            per_page: Number of items per page.
            active_only: If True, return only active schedules.

        Returns:
            Tuple of (schedule list, total count).
        """
        query = self._db.query(Schedule).filter(Schedule.user_id == user_id)

        if active_only:
            query = query.filter(Schedule.is_active.is_(True))

        total = query.count()
        schedules = (
            query.order_by(Schedule.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return schedules, total

    def update_schedule(
        self, user_id: uuid.UUID, schedule_id: uuid.UUID, request: ScheduleUpdateRequest
    ) -> Schedule:
        """Update a schedule owned by the user.

        Args:
            user_id: The current user's UUID.
            schedule_id: The schedule's UUID.
            request: Update parameters (only provided fields are changed).

        Returns:
            The updated Schedule ORM instance.

        Raises:
            NotFoundError: If schedule not found or not owned by user.
        """
        schedule = self.get_schedule(user_id, schedule_id)

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(schedule, field, value)

        # Recalculate next_run_at if cron changed
        if "cron_expression" in update_data:
            schedule.next_run_at = self._calculate_next_run(schedule.cron_expression)

        self._db.commit()
        self._db.refresh(schedule)

        logger.info("Schedule updated: %s (id=%s)", schedule.name, schedule.id)
        return schedule

    def delete_schedule(self, user_id: uuid.UUID, schedule_id: uuid.UUID) -> None:
        """Delete a schedule owned by the user.

        Args:
            user_id: The current user's UUID.
            schedule_id: The schedule's UUID.

        Raises:
            NotFoundError: If schedule not found or not owned by user.
        """
        schedule = self.get_schedule(user_id, schedule_id)
        self._db.delete(schedule)
        self._db.commit()
        logger.info("Schedule deleted: %s", schedule_id)

    def toggle_schedule(self, user_id: uuid.UUID, schedule_id: uuid.UUID) -> Schedule:
        """Toggle a schedule's active state.

        Args:
            user_id: The current user's UUID.
            schedule_id: The schedule's UUID.

        Returns:
            The updated Schedule with toggled is_active.

        Raises:
            NotFoundError: If schedule not found or not owned by user.
        """
        schedule = self.get_schedule(user_id, schedule_id)
        schedule.is_active = not schedule.is_active

        if schedule.is_active:
            schedule.next_run_at = self._calculate_next_run(schedule.cron_expression)
        else:
            schedule.next_run_at = None

        self._db.commit()
        self._db.refresh(schedule)

        logger.info(
            "Schedule %s toggled to %s",
            schedule_id,
            "active" if schedule.is_active else "inactive",
        )
        return schedule

    def get_due_schedules(self) -> list[Schedule]:
        """Return all active schedules whose next_run_at is in the past.

        Returns:
            List of schedules ready to be executed.
        """
        now = datetime.now(UTC)
        return (
            self._db.query(Schedule)
            .filter(
                Schedule.is_active.is_(True),
                Schedule.next_run_at <= now,
            )
            .all()
        )

    def mark_schedule_run(self, schedule: Schedule) -> None:
        """Update schedule timestamps after a successful run.

        Args:
            schedule: The schedule that was just executed.
        """
        now = datetime.now(UTC)
        schedule.last_run_at = now
        schedule.next_run_at = self._calculate_next_run(schedule.cron_expression)
        self._db.commit()

    @staticmethod
    def _calculate_next_run(cron_expression: str) -> datetime:
        """Calculate the next execution time from a cron expression.

        Args:
            cron_expression: Standard cron expression string.

        Returns:
            Next execution datetime in UTC.
        """
        now = datetime.now(UTC)
        cron = croniter(cron_expression, now)
        next_run: datetime = cron.get_next(datetime)  # type: ignore[assignment]
        return next_run
