"""Authentication service for user registration and login."""

import logging
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

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

    def __init__(self, db: Session) -> None:
        self._db = db

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
