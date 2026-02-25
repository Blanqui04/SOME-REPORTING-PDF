"""S3 / MinIO object storage service for PDF reports.

Stores generated PDF files in an S3-compatible bucket instead of
(or in addition to) PostgreSQL, improving scalability for large
report volumes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from backend.app.core.config import Settings

logger = logging.getLogger(__name__)

# S3 operations use simple REST calls via httpx so we don't need
# the heavyweight ``boto3`` dependency.  For production use-cases
# with AWS SigV4 auth, install ``boto3`` and swap this out.

_TIMEOUT = 30


class S3StorageService:
    """Thin wrapper around S3/MinIO HTTP API for PDF storage.

    Args:
        settings: Application settings containing S3 configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
        self._bucket = settings.S3_BUCKET_NAME
        self._access_key = settings.S3_ACCESS_KEY
        self._secret_key = settings.S3_SECRET_KEY
        self._region = settings.S3_REGION
        self._enabled = settings.S3_ENABLED

    @property
    def enabled(self) -> bool:
        """Return True if S3 storage is configured and enabled."""
        return self._enabled and bool(self._endpoint)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_pdf(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        """Upload PDF bytes to S3 and return the object URL.

        Args:
            key: Object key (e.g. ``reports/2026/01/report_abc.pdf``).
            data: Raw PDF bytes.
            content_type: MIME type for the upload.

        Returns:
            Full URL of the uploaded object.

        Raises:
            RuntimeError: If the upload fails.
        """
        if not self.enabled:
            raise RuntimeError("S3 storage is not enabled")

        url = f"{self._endpoint}/{self._bucket}/{key}"

        try:
            response = httpx.put(
                url,
                content=data,
                headers={
                    "Content-Type": content_type,
                    "X-Amz-Content-Sha256": "UNSIGNED-PAYLOAD",
                },
                auth=(self._access_key, self._secret_key) if self._access_key else None,
                timeout=_TIMEOUT,
            )
            if response.is_success:
                logger.info("Uploaded %s to S3 (%d bytes)", key, len(data))
                return url
            raise RuntimeError(
                f"S3 upload failed ({response.status_code}): {response.text[:200]}"
            )
        except httpx.HTTPError as exc:
            logger.error("S3 upload error for %s: %s", key, exc)
            raise RuntimeError(f"S3 upload error: {exc}") from exc

    def download_pdf(self, key: str) -> bytes:
        """Download a PDF from S3.

        Args:
            key: Object key.

        Returns:
            Raw PDF bytes.

        Raises:
            RuntimeError: If the download fails.
        """
        if not self.enabled:
            raise RuntimeError("S3 storage is not enabled")

        url = f"{self._endpoint}/{self._bucket}/{key}"

        try:
            response = httpx.get(
                url,
                auth=(self._access_key, self._secret_key) if self._access_key else None,
                timeout=_TIMEOUT,
            )
            if response.is_success:
                logger.info("Downloaded %s from S3 (%d bytes)", key, len(response.content))
                return response.content
            raise RuntimeError(
                f"S3 download failed ({response.status_code}): {response.text[:200]}"
            )
        except httpx.HTTPError as exc:
            logger.error("S3 download error for %s: %s", key, exc)
            raise RuntimeError(f"S3 download error: {exc}") from exc

    def delete_pdf(self, key: str) -> bool:
        """Delete a PDF from S3.

        Args:
            key: Object key.

        Returns:
            True if deletion succeeded.
        """
        if not self.enabled:
            return False

        url = f"{self._endpoint}/{self._bucket}/{key}"

        try:
            response = httpx.delete(
                url,
                auth=(self._access_key, self._secret_key) if self._access_key else None,
                timeout=_TIMEOUT,
            )
            if response.is_success:
                logger.info("Deleted %s from S3", key)
                return True
            logger.warning("S3 delete returned %s for %s", response.status_code, key)
        except httpx.HTTPError as exc:
            logger.error("S3 delete error for %s: %s", key, exc)
        return False

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL.

        Note: For MinIO/S3, this builds a simple URL with expiration
        parameters.  For production AWS use, switch to ``boto3``'s
        ``generate_presigned_url()``.

        Args:
            key: Object key.
            expires_in: URL validity in seconds.

        Returns:
            Presigned URL string.
        """
        return f"{self._endpoint}/{self._bucket}/{key}?expires={expires_in}"

    def generate_key(self, report_id: str, file_name: str) -> str:
        """Generate a consistent S3 object key for a report.

        Args:
            report_id: UUID of the report.
            file_name: Original file name.

        Returns:
            Object key path.
        """
        return f"reports/{report_id}/{file_name}"
