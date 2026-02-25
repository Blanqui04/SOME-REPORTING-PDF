"""JWT token management and password hashing utilities."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to verify.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def create_access_token(
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The token subject (typically user ID).
        secret_key: The secret key used for signing.
        algorithm: The JWT signing algorithm.
        expires_delta: Token expiration duration. Defaults to 30 minutes.

    Returns:
        Encoded JWT token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=30)

    expire = datetime.now(UTC) + expires_delta
    to_encode = {"sub": subject, "exp": expire}
    encoded_jwt = cast(str, jwt.encode(to_encode, secret_key, algorithm=algorithm))
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> str:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode.
        secret_key: The secret key used for verification.
        algorithm: The JWT signing algorithm.

    Returns:
        The token subject (user ID).

    Raises:
        AuthenticationError: If the token is invalid or expired.
    """
    try:
        payload = cast(dict[str, Any], jwt.decode(token, secret_key, algorithms=[algorithm]))
        subject: str | None = payload.get("sub")
        if subject is None:
            raise AuthenticationError("Token missing subject claim")
        return subject
    except JWTError as e:
        logger.warning("JWT decode error: %s", e)
        raise AuthenticationError("Invalid or expired token") from e
