"""PDF Template API endpoints."""

import base64
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.pdf_template import (
    TemplateCreateRequest,
    TemplateResponse,
    TemplateUploadPDFRequest,
)
from backend.app.services.template_service import TemplateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    request: TemplateCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateResponse:
    """Create a new PDF template with branding settings.

    Args:
        request: Template creation parameters.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Created template metadata.
    """
    service = TemplateService(db)
    template = service.create_template(
        user_id=current_user.id,
        data=request.model_dump(exclude_none=True),
    )
    return TemplateResponse.from_model(template)


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TemplateResponse]:
    """List all PDF templates for the current user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of template metadata.
    """
    service = TemplateService(db)
    templates = service.list_templates(user_id=current_user.id)
    return [TemplateResponse.from_model(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateResponse:
    """Get a single template by ID.

    Args:
        template_id: Template UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Template metadata.
    """
    service = TemplateService(db)
    template = service.get_template(user_id=current_user.id, template_id=template_id)
    return TemplateResponse.from_model(template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: uuid.UUID,
    request: TemplateCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateResponse:
    """Update an existing template.

    Args:
        template_id: Template UUID.
        request: Updated template data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated template metadata.
    """
    service = TemplateService(db)
    template = service.update_template(
        user_id=current_user.id,
        template_id=template_id,
        data=request.model_dump(exclude_none=True),
    )
    return TemplateResponse.from_model(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a template.

    Args:
        template_id: Template UUID.
        current_user: Authenticated user.
        db: Database session.
    """
    service = TemplateService(db)
    service.delete_template(user_id=current_user.id, template_id=template_id)


@router.post("/{template_id}/upload-pdf", response_model=TemplateResponse)
def upload_base_pdf(
    template_id: uuid.UUID,
    request: TemplateUploadPDFRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateResponse:
    """Upload a base PDF to a template for panel overlay.

    Args:
        template_id: Template UUID.
        request: Base64-encoded PDF and filename.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated template metadata.
    """
    service = TemplateService(db)
    template = service.upload_base_pdf(
        user_id=current_user.id,
        template_id=template_id,
        pdf_b64=request.base_pdf_base64,
        filename=request.base_pdf_name,
    )
    return TemplateResponse.from_model(template)


@router.post("/{template_id}/upload-pdf-file", response_model=TemplateResponse)
async def upload_base_pdf_file(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(description="PDF file to use as base template"),  # noqa: B008
) -> TemplateResponse:
    """Upload a base PDF via multipart form-data (native file picker).

    Accepts a raw PDF file upload instead of base64 encoding,
    which is faster and more natural for large files.

    Args:
        template_id: Template UUID.
        current_user: Authenticated user.
        db: Database session.
        file: Uploaded PDF file.

    Returns:
        Updated template metadata.
    """
    contents = await file.read()
    pdf_b64 = base64.b64encode(contents).decode("utf-8")
    service = TemplateService(db)
    template = service.upload_base_pdf(
        user_id=current_user.id,
        template_id=template_id,
        pdf_b64=pdf_b64,
        filename=file.filename or "uploaded.pdf",
    )
    return TemplateResponse.from_model(template)


@router.delete("/{template_id}/base-pdf", status_code=status.HTTP_204_NO_CONTENT)
def remove_base_pdf(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Remove the base PDF from a template.

    Args:
        template_id: Template UUID.
        current_user: Authenticated user.
        db: Database session.
    """
    service = TemplateService(db)
    service.remove_base_pdf(user_id=current_user.id, template_id=template_id)


@router.get("/{template_id}/logo")
def get_template_logo(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Get the logo data for a template.

    Args:
        template_id: Template UUID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Dict with logo_base64 and logo_mime_type.
    """
    service = TemplateService(db)
    template = service.get_template(user_id=current_user.id, template_id=template_id)
    return {
        "logo_base64": template.logo_base64,
        "logo_mime_type": template.logo_mime_type,
    }
