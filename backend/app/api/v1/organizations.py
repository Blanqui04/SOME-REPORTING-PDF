"""Organization API endpoints for multi-tenant management."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User
from backend.app.services.org_service import OrganizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrgCreateRequest(BaseModel):
    """Request body for creating an organization."""

    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    max_users: int = Field(default=0, ge=0)


class OrgMemberRequest(BaseModel):
    """Request body for adding a member to an organization."""

    user_id: uuid.UUID
    role: str = Field(default="viewer", pattern=r"^(owner|admin|editor|viewer)$")


class OrgResponse(BaseModel):
    """Response schema for an organization."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    max_users: int

    model_config = {"from_attributes": True}


class OrgMemberResponse(BaseModel):
    """Response schema for an organization member."""

    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    org_role: str

    model_config = {"from_attributes": True}


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrgCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrgResponse:
    """Create a new organization. The creator becomes the owner."""
    service = OrganizationService(db)
    org = service.create_organization(
        name=request.name,
        owner_id=current_user.id,
        description=request.description,
        max_users=request.max_users,
    )
    return OrgResponse.model_validate(org)


@router.get("", response_model=list[OrgResponse])
def list_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[OrgResponse]:
    """List organizations the current user belongs to."""
    service = OrganizationService(db)
    orgs = service.list_user_organizations(current_user.id)
    return [OrgResponse.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrgResponse)
def get_organization(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrgResponse:
    """Get organization details by ID."""
    service = OrganizationService(db)
    org = service.get_organization(org_id)
    return OrgResponse.model_validate(org)


@router.post(
    "/{org_id}/members",
    response_model=OrgMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    org_id: uuid.UUID,
    request: OrgMemberRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrgMemberResponse:
    """Add a user to the organization."""
    service = OrganizationService(db)
    member = service.add_member(org_id, request.user_id, request.role)
    return OrgMemberResponse.model_validate(member)


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove a user from the organization."""
    service = OrganizationService(db)
    service.remove_member(org_id, user_id)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an organization (admin only)."""
    service = OrganizationService(db)
    service.delete_organization(org_id)
