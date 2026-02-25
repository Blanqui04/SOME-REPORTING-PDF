"""TOTP-based Two-Factor Authentication service.

Provides functions to generate TOTP secrets, create QR codes for
authenticator apps, and verify TOTP tokens.
"""

import base64
import io
import logging

import pyotp
import qrcode  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class TOTPService:
    """Manages TOTP secret generation, QR codes, and token verification.

    Args:
        issuer: The TOTP issuer name shown in authenticator apps.
    """

    def __init__(self, issuer: str = "Grafana PDF Reporter") -> None:
        self._issuer = issuer

    def generate_secret(self) -> str:
        """Generate a new random TOTP secret.

        Returns:
            Base32-encoded secret string.
        """
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """Build the otpauth:// URI for authenticator apps.

        Args:
            secret: The TOTP secret.
            email: The user's email (used as account name).

        Returns:
            The otpauth:// provisioning URI.
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=self._issuer)

    def generate_qr_base64(self, secret: str, email: str) -> str:
        """Generate a QR code image as a base64-encoded PNG.

        Args:
            secret: The TOTP secret.
            email: The user's email.

        Returns:
            Base64-encoded PNG image string.
        """
        uri = self.get_provisioning_uri(secret, email)
        qr = qrcode.make(uri)

        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8")

    def verify_token(self, secret: str, token: str) -> bool:
        """Verify a TOTP token against the secret.

        Allows a window of 1 time step (30s) for clock skew.

        Args:
            secret: The user's TOTP secret.
            token: The 6-digit token to verify.

        Returns:
            True if the token is valid.
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
