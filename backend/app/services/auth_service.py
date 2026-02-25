"""Authentication service for user registration and login.

Supports local authentication and LDAP/AD with JIT provisioning.
"""

import logging
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from backend.app.core.security import hash_password, verify_password
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user authentication and registration business logic.

    Args:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings

    def register_user(self, user_data: UserCreate) -> User:
        """Create a new user after validating uniqueness.

        Args:
            user_data: Validated registration data.

        Returns:
            The newly created User ORM instance.

        Raises:
            ConflictError: If email or username already exists.
        """
        existing = (
            self._db.query(User)
            .filter(or_(User.email == user_data.email, User.username == user_data.username))
            .first()
        )

        if existing is not None:
            if existing.email == user_data.email:
                raise ConflictError(f"Email '{user_data.email}' is already registered")
            raise ConflictError(f"Username '{user_data.username}' is already taken")

        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hash_password(user_data.password),
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)

        logger.info("User registered: %s (id=%s)", user.username, user.id)
        return user

    def authenticate_user(self, username: str, password: str) -> User:
        """Verify credentials and return the user.

        The username field accepts either username or email for login.

        Args:
            username: The username or email address.
            password: The plaintext password.

        Returns:
            The authenticated User ORM instance.

        Raises:
            AuthenticationError: If credentials are invalid or user is inactive.
        """
        user = (
            self._db.query(User)
            .filter(or_(User.username == username, User.email == username))
            .first()
        )

        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid username or password")

        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        logger.info("User authenticated: %s", user.username)
        return user

    def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Fetch a user by their UUID.

        Args:
            user_id: The user's UUID.

        Returns:
            The User ORM instance.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self._db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    def authenticate_ldap(self, username: str, password: str) -> User:
        """Authenticate via LDAP/AD with JIT user provisioning.

        If the user doesn't exist locally, a record is created
        with auth_provider='ldap' and a random password hash.

        Args:
            username: The LDAP username (sAMAccountName).
            password: The plaintext LDAP password.

        Returns:
            The authenticated (or newly provisioned) User.

        Raises:
            AuthenticationError: If LDAP authentication fails.
        """
        if not self._settings or not self._settings.LDAP_ENABLED:
            raise AuthenticationError("LDAP authentication is not enabled")

        from backend.app.services.ldap_service import LDAPService

        ldap_svc = LDAPService(self._settings)
        result = ldap_svc.authenticate(username, password)

        if not result.success:
            raise AuthenticationError(result.error or "LDAP authentication failed")

        # JIT provisioning: create local user if not exists
        user = (
            self._db.query(User)
            .filter(or_(User.username == result.username, User.email == result.email))
            .first()
        )

        if user is None:
            user = User(
                email=result.email,
                username=result.username,
                hashed_password=hash_password(uuid.uuid4().hex),
                auth_provider="ldap",
                role=self._settings.LDAP_DEFAULT_ROLE,
            )
            self._db.add(user)
            self._db.commit()
            self._db.refresh(user)
            logger.info("LDAP JIT provisioned user: %s", result.username)
        else:
            # Update auth_provider if user was previously local
            if user.auth_provider != "ldap":
                user.auth_provider = "ldap"
                self._db.commit()

        logger.info("LDAP user authenticated: %s", result.username)
        return user

    def setup_totp(self, user_id: uuid.UUID) -> tuple[str, str, str]:
        """Generate a TOTP secret and QR code for the user.

        Args:
            user_id: The user's UUID.

        Returns:
            Tuple of (secret, qr_code_base64, provisioning_uri).
        """
        from backend.app.services.totp_service import TOTPService

        user = self.get_user_by_id(user_id)
        issuer = self._settings.TOTP_ISSUER if self._settings else "Grafana PDF Reporter"
        totp_svc = TOTPService(issuer=issuer)

        secret = totp_svc.generate_secret()
        qr_base64 = totp_svc.generate_qr_base64(secret, user.email)
        uri = totp_svc.get_provisioning_uri(secret, user.email)

        return secret, qr_base64, uri

    def enable_totp(self, user_id: uuid.UUID, secret: str, token: str) -> bool:
        """Enable TOTP for a user after verifying the initial token.

        Args:
            user_id: The user's UUID.
            secret: The TOTP secret from setup.
            token: The 6-digit verification token.

        Returns:
            True if TOTP was enabled successfully.

        Raises:
            AuthenticationError: If the token is invalid.
        """
        from backend.app.services.totp_service import TOTPService

        issuer = self._settings.TOTP_ISSUER if self._settings else "Grafana PDF Reporter"
        totp_svc = TOTPService(issuer=issuer)

        if not totp_svc.verify_token(secret, token):
            raise AuthenticationError("Invalid TOTP token")

        user = self.get_user_by_id(user_id)
        user.totp_secret = secret
        user.totp_enabled = True
        self._db.commit()

        logger.info("TOTP enabled for user: %s", user.username)
        return True

    def disable_totp(self, user_id: uuid.UUID) -> bool:
        """Disable TOTP for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            True if TOTP was disabled.
        """
        user = self.get_user_by_id(user_id)
        user.totp_secret = None
        user.totp_enabled = False
        self._db.commit()

        logger.info("TOTP disabled for user: %s", user.username)
        return True

    def verify_totp(self, user_id: uuid.UUID, token: str) -> bool:
        """Verify a TOTP token for an authenticated user.

        Args:
            user_id: The user's UUID.
            token: The 6-digit TOTP token.

        Returns:
            True if the token is valid.

        Raises:
            AuthenticationError: If TOTP is not enabled or token is invalid.
        """
        from backend.app.services.totp_service import TOTPService

        user = self.get_user_by_id(user_id)
        if not user.totp_enabled or not user.totp_secret:
            raise AuthenticationError("TOTP is not enabled for this user")

        issuer = self._settings.TOTP_ISSUER if self._settings else "Grafana PDF Reporter"
        totp_svc = TOTPService(issuer=issuer)

        if not totp_svc.verify_token(user.totp_secret, token):
            raise AuthenticationError("Invalid TOTP token")

        return True
