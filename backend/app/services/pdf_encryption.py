"""PDF encryption utility using pypdf.

Provides functions to encrypt PDF documents with user and owner
passwords using AES-256 encryption.
"""

import logging

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def encrypt_pdf(
    pdf_data: bytes,
    user_password: str,
    owner_password: str | None = None,
) -> bytes:
    """Encrypt a PDF with AES-256 encryption.

    Args:
        pdf_data: The raw PDF bytes to encrypt.
        user_password: Password required to open the PDF.
        owner_password: Owner password for full permissions.
            Defaults to the user_password if not provided.

    Returns:
        Encrypted PDF bytes.
    """
    import io

    reader = PdfReader(io.BytesIO(pdf_data))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Copy metadata
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    writer.encrypt(
        user_password=user_password,
        owner_password=owner_password or user_password,
        algorithm="AES-256",
    )

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    encrypted = output.read()
    logger.info(
        "PDF encrypted: %d bytes → %d bytes",
        len(pdf_data),
        len(encrypted),
    )
    return encrypted
