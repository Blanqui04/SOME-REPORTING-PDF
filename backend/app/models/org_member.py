"""Organization membership model linking users to organizations."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.user import User


class OrgMember(UUIDMixin, TimestampMixin, Base):
    """Maps a user to an organization with a per-org role.

    Attributes:
        user_id: FK to users table.
        organization_id: FK to organizations table.
        org_role: Role within this organization (owner/admin/editor/viewer).
        user: Relationship to User.
        organization: Relationship to Organization.
    """

    __tablename__ = "org_members"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_org_member"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    org_role: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False)

    user: Mapped[User] = relationship(back_populates="org_memberships", lazy="selectin")
    organization: Mapped[Organization] = relationship(
        back_populates="members", lazy="selectin"
    )
