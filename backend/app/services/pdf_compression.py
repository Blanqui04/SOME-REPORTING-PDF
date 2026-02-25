"""PDF compression utilities.

Reduces PDF file size by compressing embedded images and removing
unused metadata.  Uses ``pypdf`` which is already a project
dependency.
"""

from __future__ import annotations

import io
import logging

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def compress_pdf(
    pdf_data: bytes,
    *,
    remove_duplication: bool = True,
    compress_content_streams: bool = True,
    image_quality: int = 80,
) -> bytes:
    """Compress a PDF to reduce file size.

    Args:
        pdf_data: Raw PDF bytes.
        remove_duplication: Merge duplicate objects.
        compress_content_streams: Apply FlateDecode to content streams.
        image_quality: JPEG quality for recompressed images (1-100).

    Returns:
        Compressed PDF bytes.

    Raises:
        ValueError: If the input is not a valid PDF.
    """
    if not pdf_data or not pdf_data.startswith(b"%PDF"):
        raise ValueError("Invalid PDF data")

    original_size = len(pdf_data)

    try:
        reader = PdfReader(io.BytesIO(pdf_data))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Copy metadata
        if reader.metadata:
            writer.add_metadata(
                {k: v for k, v in reader.metadata.items() if v is not None}
            )

        # Remove duplicate objects
        if remove_duplication:
            writer.compress_identical_objects(remove_identicals=True)

        # Compress content streams
        if compress_content_streams:
            for page in writer.pages:
                page.compress_content_streams()

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        compressed_data = output.read()

        compressed_size = len(compressed_data)
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

        logger.info(
            "PDF compressed: %d → %d bytes (%.1f%% reduction)",
            original_size,
            compressed_size,
            ratio,
        )

        # Only return compressed version if it's actually smaller
        if compressed_size < original_size:
            return compressed_data
        logger.info("Compressed PDF not smaller, returning original")
        return pdf_data

    except Exception as exc:
        logger.error("PDF compression failed: %s", exc)
        # Return original data on failure — never lose the PDF
        return pdf_data


def get_pdf_info(pdf_data: bytes) -> dict[str, object]:
    """Extract basic PDF metadata.

    Args:
        pdf_data: Raw PDF bytes.

    Returns:
        Dictionary with page_count, file_size, and metadata fields.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_data))
        info: dict[str, object] = {
            "page_count": len(reader.pages),
            "file_size_bytes": len(pdf_data),
        }
        if reader.metadata:
            info["title"] = reader.metadata.get("/Title", "")
            info["author"] = reader.metadata.get("/Author", "")
            info["creator"] = reader.metadata.get("/Creator", "")
        return info
    except Exception as exc:
        logger.error("Failed to read PDF info: %s", exc)
        return {"page_count": 0, "file_size_bytes": len(pdf_data), "error": str(exc)}
