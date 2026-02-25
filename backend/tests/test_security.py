"""Tests for JWT token management and password hashing utilities."""

from datetime import timedelta

import pytest

from backend.app.core.exceptions import AuthenticationError
from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET = "test-secret-key-for-unit-tests"


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_string(self) -> None:
        hashed = hash_password("mysecretpassword")
        assert isinstance(hashed, str)
        assert hashed != "mysecretpassword"

    def test_hash_password_different_hashes(self) -> None:
        h1 = hash_password("password123")
        h2 = hash_password("password123")
        # bcrypt produces different salts each time
        assert h1 != h2

    def test_verify_password_correct(self) -> None:
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_password_incorrect(self) -> None:
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self) -> None:
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False


class TestAccessToken:
    """Tests for JWT token creation and decoding."""

    def test_create_and_decode_token(self) -> None:
        token = create_access_token(subject="user-123", secret_key=SECRET)
        subject = decode_access_token(token=token, secret_key=SECRET)
        assert subject == "user-123"

    def test_create_token_with_custom_expiry(self) -> None:
        token = create_access_token(
            subject="user-456",
            secret_key=SECRET,
            expires_delta=timedelta(hours=2),
        )
        subject = decode_access_token(token=token, secret_key=SECRET)
        assert subject == "user-456"

    def test_decode_token_wrong_secret(self) -> None:
        token = create_access_token(subject="user-789", secret_key=SECRET)
        with pytest.raises(AuthenticationError, match="Invalid or expired token"):
            decode_access_token(token=token, secret_key="wrong-secret")

    def test_decode_token_expired(self) -> None:
        token = create_access_token(
            subject="user-exp",
            secret_key=SECRET,
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(AuthenticationError, match="Invalid or expired token"):
            decode_access_token(token=token, secret_key=SECRET)

    def test_decode_token_invalid_format(self) -> None:
        with pytest.raises(AuthenticationError, match="Invalid or expired token"):
            decode_access_token(token="not.a.valid.token", secret_key=SECRET)

    def test_decode_token_missing_subject(self) -> None:
        from jose import jwt

        token = jwt.encode({"data": "no-sub"}, SECRET, algorithm="HS256")
        with pytest.raises(AuthenticationError, match="Token missing subject claim"):
            decode_access_token(token=token, secret_key=SECRET)

    def test_create_token_default_expiry(self) -> None:
        """Default expiry should be 30 minutes and token should be valid."""
        token = create_access_token(subject="default-exp", secret_key=SECRET)
        subject = decode_access_token(token=token, secret_key=SECRET)
        assert subject == "default-exp"
