"""Schedule ORM model for recurring report generation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class Schedule(UUIDMixin, TimestampMixin, Base):
    """Scheduled report generation model.

    Defines recurring report generation tasks using cron expressions.
    Supports email delivery and webhook notifications on completion.
    """

    __tablename__ = "schedules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dashboard_uid: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    panel_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    time_range_from: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_range_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # v3.1 additions
    email_recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ca", nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    width: Mapped[int] = mapped_column(default=1000, nullable=False)
    height: Mapped[int] = mapped_column(default=500, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dashboard_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    owner: Mapped[User] = relationship(back_populates="schedules")
