"""Tests for the Organization multi-tenant feature."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.services.org_service import OrganizationService, _slugify

# ── Slugify helper tests ──────────────────────────────────────────

class TestSlugify:
    """Tests for the _slugify helper."""

    def test_basic_slugify(self) -> None:
        assert _slugify("My Organization") == "my-organization"

    def test_special_characters(self) -> None:
        assert _slugify("Test! Org @#$") == "test-org"

    def test_underscores_and_spaces(self) -> None:
        assert _slugify("hello_world  test") == "hello-world-test"

    def test_already_slug(self) -> None:
        assert _slugify("already-a-slug") == "already-a-slug"

    def test_uppercase(self) -> None:
        assert _slugify("UPPERCASE") == "uppercase"

    def test_trailing_special(self) -> None:
        result = _slugify("test---")
        assert result == "test"


# ── Organization Service tests ─────────────────────────────────────

class TestOrganizationService:
    """Tests for OrganizationService."""

    def test_create_organization(self, db: Session, test_user: User) -> None:
        """Creating an org should also add the creator as owner."""
        service = OrganizationService(db)
        org = service.create_organization(
            name="Test Org",
            owner_id=test_user.id,
            description="A test organization",
        )
        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.description == "A test organization"
        assert org.is_active is True
        assert len(org.members) == 1
        assert org.members[0].user_id == test_user.id
        assert org.members[0].org_role == "owner"

    def test_create_duplicate_slug_raises(self, db: Session, test_user: User) -> None:
        """Creating two orgs with the same name should raise ConflictError."""
        from backend.app.core.exceptions import ConflictError

        service = OrganizationService(db)
        service.create_organization(name="Duplicate", owner_id=test_user.id)
        with pytest.raises(ConflictError):
            service.create_organization(name="Duplicate", owner_id=test_user.id)

    def test_get_organization(self, db: Session, test_user: User) -> None:
        """Should retrieve an org by ID."""
        service = OrganizationService(db)
        org = service.create_organization(name="Findable Org", owner_id=test_user.id)
        found = service.get_organization(org.id)
        assert found.id == org.id
        assert found.name == "Findable Org"

    def test_get_organization_not_found(self, db: Session) -> None:
        """Should raise NotFoundError for unknown ID."""
        from backend.app.core.exceptions import NotFoundError

        service = OrganizationService(db)
        with pytest.raises(NotFoundError):
            service.get_organization(uuid.uuid4())

    def test_get_by_slug(self, db: Session, test_user: User) -> None:
        """Should retrieve an org by slug."""
        service = OrganizationService(db)
        service.create_organization(name="Slug Test", owner_id=test_user.id)
        found = service.get_by_slug("slug-test")
        assert found.name == "Slug Test"

    def test_get_by_slug_not_found(self, db: Session) -> None:
        """Should raise NotFoundError for unknown slug."""
        from backend.app.core.exceptions import NotFoundError

        service = OrganizationService(db)
        with pytest.raises(NotFoundError):
            service.get_by_slug("nonexistent-slug")

    def test_list_user_organizations(self, db: Session, test_user: User) -> None:
        """Should list all orgs the user belongs to."""
        service = OrganizationService(db)
        service.create_organization(name="Org One", owner_id=test_user.id)
        service.create_organization(name="Org Two", owner_id=test_user.id)
        orgs = service.list_user_organizations(test_user.id)
        assert len(orgs) == 2
        names = {o.name for o in orgs}
        assert names == {"Org One", "Org Two"}

    def test_list_user_organizations_empty(self, db: Session) -> None:
        """Should return empty list for user in no orgs."""
        service = OrganizationService(db)
        orgs = service.list_user_organizations(uuid.uuid4())
        assert orgs == []

    def test_add_member(self, db: Session, test_user: User) -> None:
        """Should add a new member to an org."""
        service = OrganizationService(db)
        org = service.create_organization(name="Add Member Org", owner_id=test_user.id)

        # Create another user
        new_user = User(
            id=uuid.uuid4(),
            email="member@example.com",
            username="memberuser",
            hashed_password="hashed",
            is_active=True,
        )
        db.add(new_user)
        db.commit()

        member = service.add_member(org.id, new_user.id, role="editor")
        assert member.user_id == new_user.id
        assert member.org_role == "editor"

    def test_add_duplicate_member_raises(self, db: Session, test_user: User) -> None:
        """Should raise ConflictError when adding an existing member."""
        from backend.app.core.exceptions import ConflictError

        service = OrganizationService(db)
        org = service.create_organization(name="Dup Member", owner_id=test_user.id)
        with pytest.raises(ConflictError):
            service.add_member(org.id, test_user.id, role="viewer")

    def test_remove_member(self, db: Session, test_user: User) -> None:
        """Should remove a member from the org."""
        service = OrganizationService(db)
        org = service.create_organization(name="Remove Org", owner_id=test_user.id)

        new_user = User(
            id=uuid.uuid4(),
            email="removable@example.com",
            username="removableuser",
            hashed_password="hashed",
            is_active=True,
        )
        db.add(new_user)
        db.commit()

        service.add_member(org.id, new_user.id, role="viewer")
        service.remove_member(org.id, new_user.id)

        orgs = service.list_user_organizations(new_user.id)
        assert len(orgs) == 0

    def test_remove_nonexistent_member(self, db: Session, test_user: User) -> None:
        """Should raise NotFoundError when removing unknown membership."""
        from backend.app.core.exceptions import NotFoundError

        service = OrganizationService(db)
        org = service.create_organization(name="No Remove Org", owner_id=test_user.id)
        with pytest.raises(NotFoundError):
            service.remove_member(org.id, uuid.uuid4())

    def test_delete_organization(self, db: Session, test_user: User) -> None:
        """Should delete the org and cascade-delete members."""
        service = OrganizationService(db)
        org = service.create_organization(name="Delete Me Org", owner_id=test_user.id)
        org_id = org.id
        service.delete_organization(org_id)

        from backend.app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            service.get_organization(org_id)

    def test_delete_nonexistent_org(self, db: Session) -> None:
        """Should raise NotFoundError for unknown org."""
        from backend.app.core.exceptions import NotFoundError

        service = OrganizationService(db)
        with pytest.raises(NotFoundError):
            service.delete_organization(uuid.uuid4())

    def test_max_users_field(self, db: Session, test_user: User) -> None:
        """Should persist max_users."""
        service = OrganizationService(db)
        org = service.create_organization(
            name="Limited Org",
            owner_id=test_user.id,
            max_users=10,
        )
        assert org.max_users == 10


# ── Organization API endpoint tests ────────────────────────────────

class TestOrganizationAPI:
    """Tests for organization REST API endpoints."""

    def test_create_organization_endpoint(self, authenticated_client: TestClient, test_user: User) -> None:
        """POST /api/v1/organizations should create an org."""
        response = authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "API Org", "description": "Created via API"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Org"
        assert data["slug"] == "api-org"
        assert data["is_active"] is True

    def test_list_organizations_endpoint(self, authenticated_client: TestClient, test_user: User) -> None:
        """GET /api/v1/organizations should return user's orgs."""
        authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "List Org 1"},
        )
        authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "List Org 2"},
        )
        response = authenticated_client.get("/api/v1/organizations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_organization_endpoint(self, authenticated_client: TestClient, test_user: User) -> None:
        """GET /api/v1/organizations/{id} should return org details."""
        create_resp = authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "Detail Org"},
        )
        org_id = create_resp.json()["id"]
        response = authenticated_client.get(f"/api/v1/organizations/{org_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Detail Org"

    def test_add_member_endpoint(self, authenticated_client: TestClient, test_user: User, db: Session) -> None:
        """POST /api/v1/organizations/{id}/members should add a member."""
        # Create another user
        new_user = User(
            id=uuid.uuid4(),
            email="apimember@example.com",
            username="apimember",
            hashed_password="hashed",
            is_active=True,
        )
        db.add(new_user)
        db.commit()

        create_resp = authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "Member API Org"},
        )
        org_id = create_resp.json()["id"]

        response = authenticated_client.post(
            f"/api/v1/organizations/{org_id}/members",
            json={"user_id": str(new_user.id), "role": "editor"},
        )
        assert response.status_code == 201
        assert response.json()["org_role"] == "editor"

    def test_remove_member_endpoint(self, authenticated_client: TestClient, test_user: User, db: Session) -> None:
        """DELETE /api/v1/organizations/{id}/members/{user_id} should remove."""
        new_user = User(
            id=uuid.uuid4(),
            email="removemember@example.com",
            username="removemember",
            hashed_password="hashed",
            is_active=True,
        )
        db.add(new_user)
        db.commit()

        create_resp = authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "Remove Member Org"},
        )
        org_id = create_resp.json()["id"]

        authenticated_client.post(
            f"/api/v1/organizations/{org_id}/members",
            json={"user_id": str(new_user.id), "role": "viewer"},
        )

        response = authenticated_client.delete(
            f"/api/v1/organizations/{org_id}/members/{new_user.id}"
        )
        assert response.status_code == 204

    def test_delete_organization_endpoint(self, authenticated_client: TestClient, test_user: User) -> None:
        """DELETE /api/v1/organizations/{id} should delete the org."""
        create_resp = authenticated_client.post(
            "/api/v1/organizations",
            json={"name": "Delete API Org"},
        )
        org_id = create_resp.json()["id"]

        response = authenticated_client.delete(f"/api/v1/organizations/{org_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_resp = authenticated_client.get(f"/api/v1/organizations/{org_id}")
        assert get_resp.status_code == 404

    def test_create_organization_unauthenticated(self, client: TestClient) -> None:
        """POST /api/v1/organizations without auth should fail."""
        response = client.post(
            "/api/v1/organizations",
            json={"name": "Unauth Org"},
        )
        assert response.status_code == 401
