"""Schedule ORM model (stub for Phase 5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class Schedule(UUIDMixin, TimestampMixin, Base):
    """Scheduled report generation model.

    Defines recurring report generation tasks using cron expressions.
    This is a Phase 5 stub -- the table is created but no API endpoints exist yet.
    """

    __tablename__ = "schedules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dashboard_uid: Mapped[str] = mapped_column(String(100), nullable=False)
    panel_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    time_range_from: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_range_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
