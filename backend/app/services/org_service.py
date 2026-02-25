"""Organization management service for multi-tenant support.

Provides CRUD operations for organizations and membership management.
"""

import logging
import re
import uuid

from sqlalchemy.orm import Session

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.models.org_member import OrgMember
from backend.app.models.organization import Organization

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert a name into a URL-safe slug.

    Args:
        name: Organization name to slugify.

    Returns:
        Lowercase slug with hyphens.
    """
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-")


class OrganizationService:
    """Handles organization and membership business logic."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_organization(
        self,
        name: str,
        owner_id: uuid.UUID,
        description: str | None = None,
        max_users: int = 0,
    ) -> Organization:
        """Create a new organization and add the creator as owner.

        Args:
            name: Organization display name.
            owner_id: UUID of the creating user.
            description: Optional description.
            max_users: User limit (0 = unlimited).

        Returns:
            Created Organization instance.

        Raises:
            ConflictError: If slug already exists.
        """
        slug = _slugify(name)
        existing = self._db.query(Organization).filter(Organization.slug == slug).first()
        if existing is not None:
            raise ConflictError(f"Organization with slug '{slug}' already exists")

        org = Organization(
            name=name,
            slug=slug,
            description=description,
            max_users=max_users,
        )
        self._db.add(org)
        self._db.flush()

        member = OrgMember(
            user_id=owner_id,
            organization_id=org.id,
            org_role="owner",
        )
        self._db.add(member)
        self._db.commit()
        self._db.refresh(org)
        logger.info("Organization created: %s (slug=%s, owner=%s)", name, slug, owner_id)
        return org

    def get_organization(self, org_id: uuid.UUID) -> Organization:
        """Fetch an organization by ID.

        Args:
            org_id: Organization UUID.

        Returns:
            Organization instance.

        Raises:
            NotFoundError: If not found.
        """
        org = self._db.query(Organization).filter(Organization.id == org_id).first()
        if org is None:
            raise NotFoundError("Organization", str(org_id))
        return org

    def get_by_slug(self, slug: str) -> Organization:
        """Fetch an organization by slug.

        Args:
            slug: URL-safe organization identifier.

        Returns:
            Organization instance.

        Raises:
            NotFoundError: If not found.
        """
        org = self._db.query(Organization).filter(Organization.slug == slug).first()
        if org is None:
            raise NotFoundError("Organization", slug)
        return org

    def list_user_organizations(self, user_id: uuid.UUID) -> list[Organization]:
        """List all organizations a user belongs to.

        Args:
            user_id: UUID of the user.

        Returns:
            List of Organization instances.
        """
        memberships = (
            self._db.query(OrgMember)
            .filter(OrgMember.user_id == user_id)
            .all()
        )
        return [m.organization for m in memberships]

    def add_member(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "viewer",
    ) -> OrgMember:
        """Add a user to an organization.

        Args:
            org_id: Organization UUID.
            user_id: User UUID.
            role: Role within the organization.

        Returns:
            Created OrgMember instance.

        Raises:
            ConflictError: If user is already a member.
            NotFoundError: If organization not found.
        """
        self.get_organization(org_id)

        existing = (
            self._db.query(OrgMember)
            .filter(OrgMember.organization_id == org_id, OrgMember.user_id == user_id)
            .first()
        )
        if existing is not None:
            raise ConflictError("User is already a member of this organization")

        member = OrgMember(
            user_id=user_id,
            organization_id=org_id,
            org_role=role,
        )
        self._db.add(member)
        self._db.commit()
        self._db.refresh(member)
        logger.info("Member added: user=%s org=%s role=%s", user_id, org_id, role)
        return member

    def remove_member(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Remove a user from an organization.

        Args:
            org_id: Organization UUID.
            user_id: User UUID.

        Raises:
            NotFoundError: If membership not found.
        """
        member = (
            self._db.query(OrgMember)
            .filter(OrgMember.organization_id == org_id, OrgMember.user_id == user_id)
            .first()
        )
        if member is None:
            raise NotFoundError("OrgMember", f"{org_id}/{user_id}")
        self._db.delete(member)
        self._db.commit()
        logger.info("Member removed: user=%s org=%s", user_id, org_id)

    def delete_organization(self, org_id: uuid.UUID) -> None:
        """Delete an organization and all its members.

        Args:
            org_id: Organization UUID.

        Raises:
            NotFoundError: If organization not found.
        """
        org = self.get_organization(org_id)
        self._db.delete(org)
        self._db.commit()
        logger.info("Organization deleted: %s", org_id)
