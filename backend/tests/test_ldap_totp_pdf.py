"""Tests for LDAP, TOTP 2FA, and PDF encryption features."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.services.auth_service import AuthService
from backend.app.services.pdf_encryption import encrypt_pdf
from backend.app.services.totp_service import TOTPService

# ---------------------------------------------------------------------------
# TOTP Service
# ---------------------------------------------------------------------------


class TestTOTPService:
    """Unit tests for TOTPService."""

    def test_generate_secret(self) -> None:
        svc = TOTPService()
        secret = svc.generate_secret()
        assert len(secret) >= 16
        assert secret.isalnum()

    def test_provisioning_uri(self) -> None:
        svc = TOTPService(issuer="TestApp")
        uri = svc.get_provisioning_uri("JBSWY3DPEHPK3PXP", "user@test.com")
        assert uri.startswith("otpauth://totp/")
        assert "TestApp" in uri
        assert "user%40test.com" in uri or "user@test.com" in uri

    def test_qr_code_base64(self) -> None:
        svc = TOTPService()
        qr = svc.generate_qr_base64("JBSWY3DPEHPK3PXP", "user@test.com")
        assert len(qr) > 100  # should be a non-trivial base64 string

    def test_verify_valid_token(self) -> None:
        import pyotp

        svc = TOTPService()
        secret = svc.generate_secret()
        totp = pyotp.TOTP(secret)
        token = totp.now()
        assert svc.verify_token(secret, token) is True

    def test_verify_invalid_token(self) -> None:
        svc = TOTPService()
        secret = svc.generate_secret()
        assert svc.verify_token(secret, "000000") is False


# ---------------------------------------------------------------------------
# Auth Service — TOTP integration
# ---------------------------------------------------------------------------


class TestAuthServiceTOTP:
    """Tests for AuthService TOTP methods."""

    def test_setup_totp(self, db: Session) -> None:
        user = User(
            email="totp@test.com",
            username="totpuser",
            hashed_password=hash_password("password123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthService(db)
        secret, qr_base64, uri = service.setup_totp(user.id)

        assert len(secret) >= 16
        assert len(qr_base64) > 100
        assert "otpauth://totp/" in uri

    def test_enable_totp(self, db: Session) -> None:
        import pyotp

        user = User(
            email="totp2@test.com",
            username="totpuser2",
            hashed_password=hash_password("password123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthService(db)
        secret, _, _ = service.setup_totp(user.id)

        # Generate valid token
        token = pyotp.TOTP(secret).now()
        result = service.enable_totp(user.id, secret, token)
        assert result is True

        db.refresh(user)
        assert user.totp_enabled is True
        assert user.totp_secret == secret

    def test_enable_totp_invalid_token(self, db: Session) -> None:
        from backend.app.core.exceptions import AuthenticationError

        user = User(
            email="totp3@test.com",
            username="totpuser3",
            hashed_password=hash_password("password123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthService(db)
        secret, _, _ = service.setup_totp(user.id)

        with pytest.raises(AuthenticationError):
            service.enable_totp(user.id, secret, "000000")

    def test_disable_totp(self, db: Session) -> None:
        user = User(
            email="totp4@test.com",
            username="totpuser4",
            hashed_password=hash_password("password123"),
            totp_enabled=True,
            totp_secret="JBSWY3DPEHPK3PXP",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthService(db)
        result = service.disable_totp(user.id)
        assert result is True

        db.refresh(user)
        assert user.totp_enabled is False
        assert user.totp_secret is None

    def test_verify_totp(self, db: Session) -> None:
        import pyotp

        secret = pyotp.random_base32()
        user = User(
            email="totp5@test.com",
            username="totpuser5",
            hashed_password=hash_password("password123"),
            totp_enabled=True,
            totp_secret=secret,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthService(db)
        token = pyotp.TOTP(secret).now()
        assert service.verify_totp(user.id, token) is True


# ---------------------------------------------------------------------------
# Auth Service — LDAP
# ---------------------------------------------------------------------------


class TestAuthServiceLDAP:
    """Tests for LDAP authentication with mocked LDAP server."""

    def test_ldap_auth_creates_user(self, db: Session, settings: Settings) -> None:
        settings.LDAP_ENABLED = True
        settings.LDAP_SERVER = "ldap.test.com"
        settings.LDAP_SEARCH_BASE = "dc=test,dc=com"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.username = "ldapuser"
        mock_result.email = "ldap@test.com"
        mock_result.display_name = "LDAP User"

        with patch(
            "backend.app.services.ldap_service.LDAPService"
        ) as mock_ldap_cls:
            mock_ldap_cls.return_value.authenticate.return_value = mock_result

            service = AuthService(db, settings)
            user = service.authenticate_ldap("ldapuser", "password")

        assert user.username == "ldapuser"
        assert user.email == "ldap@test.com"
        assert user.auth_provider == "ldap"

    def test_ldap_auth_existing_user(self, db: Session, settings: Settings) -> None:
        # Create existing user
        existing = User(
            email="ldap2@test.com",
            username="ldapuser2",
            hashed_password=hash_password("old_password"),
            auth_provider="local",
        )
        db.add(existing)
        db.commit()

        settings.LDAP_ENABLED = True
        settings.LDAP_SERVER = "ldap.test.com"
        settings.LDAP_SEARCH_BASE = "dc=test,dc=com"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.username = "ldapuser2"
        mock_result.email = "ldap2@test.com"
        mock_result.display_name = "LDAP User 2"

        with patch(
            "backend.app.services.ldap_service.LDAPService"
        ) as mock_ldap_cls:
            mock_ldap_cls.return_value.authenticate.return_value = mock_result

            service = AuthService(db, settings)
            user = service.authenticate_ldap("ldapuser2", "password")

        assert user.auth_provider == "ldap"

    def test_ldap_auth_failure(self, db: Session, settings: Settings) -> None:
        from backend.app.core.exceptions import AuthenticationError

        settings.LDAP_ENABLED = True
        settings.LDAP_SERVER = "ldap.test.com"
        settings.LDAP_SEARCH_BASE = "dc=test,dc=com"

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Invalid credentials"

        with patch(
            "backend.app.services.ldap_service.LDAPService"
        ) as mock_ldap_cls:
            mock_ldap_cls.return_value.authenticate.return_value = mock_result

            service = AuthService(db, settings)
            with pytest.raises(AuthenticationError):
                service.authenticate_ldap("baduser", "wrong")

    def test_ldap_disabled_raises(self, db: Session, settings: Settings) -> None:
        from backend.app.core.exceptions import AuthenticationError

        settings.LDAP_ENABLED = False
        service = AuthService(db, settings)
        with pytest.raises(AuthenticationError, match="not enabled"):
            service.authenticate_ldap("user", "pass")


# ---------------------------------------------------------------------------
# PDF Encryption
# ---------------------------------------------------------------------------


class TestPDFEncryption:
    """Tests for PDF encryption utility."""

    def _make_simple_pdf(self) -> bytes:
        """Create minimal valid PDF bytes for testing."""
        import io

        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        return buf.read()

    def test_encrypt_pdf(self) -> None:
        pdf_data = self._make_simple_pdf()
        encrypted = encrypt_pdf(pdf_data, user_password="test123")
        assert len(encrypted) > 0
        assert encrypted != pdf_data

    def test_encrypted_pdf_readable_with_password(self) -> None:
        import io

        from pypdf import PdfReader

        pdf_data = self._make_simple_pdf()
        encrypted = encrypt_pdf(pdf_data, user_password="mypass")

        reader = PdfReader(io.BytesIO(encrypted), password="mypass")
        assert len(reader.pages) == 1


# ---------------------------------------------------------------------------
# API Integration — TOTP Endpoints
# ---------------------------------------------------------------------------


class TestTOTPAPI:
    """Integration tests for TOTP API endpoints."""

    def test_totp_setup(self, authenticated_client: TestClient) -> None:
        response = authenticated_client.post("/api/v1/auth/totp/setup")
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code_base64" in data
        assert "provisioning_uri" in data

    def test_totp_enable_invalid_token(self, authenticated_client: TestClient) -> None:
        # First setup
        setup = authenticated_client.post("/api/v1/auth/totp/setup")
        secret = setup.json()["secret"]

        # Try to enable with invalid token
        response = authenticated_client.post(
            "/api/v1/auth/totp/enable",
            json={"secret": secret, "token": "000000"},
        )
        assert response.status_code == 401

    def test_login_returns_requires_totp(
        self, client: TestClient, db: Session
    ) -> None:
        import pyotp

        # Register user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "totp_login@test.com",
                "username": "totp_login",
                "password": "password123",
            },
        )

        # Enable TOTP directly in DB
        user = db.query(User).filter(User.username == "totp_login").first()
        assert user is not None
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.totp_enabled = True
        db.commit()

        # Login should return requires_totp=True
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "totp_login", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_totp"] is True
