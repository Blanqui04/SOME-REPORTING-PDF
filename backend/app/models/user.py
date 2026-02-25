"""User ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.org_member import OrgMember
    from backend.app.models.pdf_template import PDFTemplate
    from backend.app.models.report import Report
    from backend.app.models.schedule import Schedule


class User(UUIDMixin, TimestampMixin, Base):
    """User account model.

    Stores authentication credentials and profile information.
    Users own reports, schedules, and can generate new ones.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="editor", nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(20), default="local", nullable=False)

    reports: Mapped[list[Report]] = relationship(
        back_populates="created_by", lazy="selectin", cascade="all, delete-orphan"
    )
    pdf_templates: Mapped[list[PDFTemplate]] = relationship(
        back_populates="created_by", lazy="selectin", cascade="all, delete-orphan"
    )
    schedules: Mapped[list[Schedule]] = relationship(
        back_populates="owner", lazy="selectin", cascade="all, delete-orphan"
    )
    org_memberships: Mapped[list[OrgMember]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
