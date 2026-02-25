"""Organization model for multi-tenant support.

Each organization provides isolated data contexts with separate
users, reports, schedules, and templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.org_member import OrgMember


class Organization(UUIDMixin, TimestampMixin, Base):
    """Organization for multi-tenant data isolation.

    Attributes:
        name: Human-readable organization name.
        slug: URL-safe unique identifier.
        description: Optional organization description.
        is_active: Whether the organization is active.
        max_users: Maximum number of members (0 = unlimited).
        members: Relationship to OrgMember entries.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_users: Mapped[int] = mapped_column(default=0, nullable=False)

    members: Mapped[list[OrgMember]] = relationship(
        back_populates="organization", lazy="selectin", cascade="all, delete-orphan"
    )
