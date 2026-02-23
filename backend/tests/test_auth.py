"""Tests for authentication API endpoints."""

from fastapi.testclient import TestClient


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, client: TestClient) -> None:
        """Successful registration returns 201 with user data."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "username": "newuser",
                "password": "securepass123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["username"] == "newuser"
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client: TestClient) -> None:
        """Registration with existing email returns 409."""
        user_data = {
            "email": "dup@example.com",
            "username": "dupuser1",
            "password": "securepass123",
        }
        client.post("/api/v1/auth/register", json=user_data)

        user_data["username"] = "dupuser2"
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 409

    def test_register_duplicate_username(self, client: TestClient) -> None:
        """Registration with existing username returns 409."""
        user_data = {
            "email": "user1@example.com",
            "username": "sameuser",
            "password": "securepass123",
        }
        client.post("/api/v1/auth/register", json=user_data)

        user_data["email"] = "user2@example.com"
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 409

    def test_register_weak_password(self, client: TestClient) -> None:
        """Registration with short password returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "short",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient) -> None:
        """Registration with invalid email returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "validuser",
                "password": "securepass123",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_username(self, client: TestClient) -> None:
        """Registration with invalid username chars returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "username": "invalid user!",
                "password": "securepass123",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client: TestClient) -> None:
        """Successful login returns JWT token."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "securepass123",
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "loginuser", "password": "securepass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_email(self, client: TestClient) -> None:
        """Login with email instead of username works."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "emaillogin@example.com",
                "username": "emailloginuser",
                "password": "securepass123",
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "emaillogin@example.com", "password": "securepass123"},
        )
        assert response.status_code == 200

    def test_login_wrong_password(self, client: TestClient) -> None:
        """Login with wrong password returns 401."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@example.com",
                "username": "wronguser",
                "password": "securepass123",
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "wronguser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient) -> None:
        """Login with non-existent user returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nouser", "password": "password123"},
        )
        assert response.status_code == 401


class TestMe:
    """Tests for GET /api/v1/auth/me."""

    def test_me_authenticated(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Authenticated user can access their profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "authuser"
        assert data["email"] == "auth@example.com"

    def test_me_no_token(self, client: TestClient) -> None:
        """Request without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client: TestClient) -> None:
        """Request with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
