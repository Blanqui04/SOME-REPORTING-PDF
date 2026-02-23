"""Report ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class ReportStatus(enum.StrEnum):
    """Report generation status values."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(UUIDMixin, TimestampMixin, Base):
    """Generated PDF report model.

    Stores report metadata and the generated PDF binary data.
    Each report belongs to a user and references a Grafana dashboard.
    """

    __tablename__ = "reports"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dashboard_uid: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dashboard_title: Mapped[str] = mapped_column(String(500), nullable=False)
    panel_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    time_range_from: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_range_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReportStatus.PENDING.value
    )
    pdf_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    pdf_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[User] = relationship(back_populates="reports")
