"""PDF Template CRUD service."""

import base64
import logging
import uuid

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models.pdf_template import PDFTemplate

logger = logging.getLogger(__name__)


class TemplateService:
    """Orchestrates PDF template CRUD operations.

    Args:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_template(self, user_id: uuid.UUID, data: dict) -> PDFTemplate:
        """Create a new PDF template.

        Args:
            user_id: Owner user UUID.
            data: Template field dict from schema.

        Returns:
            The newly created PDFTemplate.
        """
        if data.get("is_default"):
            self._clear_defaults(user_id)

        template = PDFTemplate(created_by_id=user_id, **data)
        self._db.add(template)
        self._db.commit()
        self._db.refresh(template)
        logger.info("Template created: %s (id=%s)", template.name, template.id)
        return template

    def update_template(
        self, user_id: uuid.UUID, template_id: uuid.UUID, data: dict
    ) -> PDFTemplate:
        """Update an existing template.

        Args:
            user_id: Owner user UUID.
            template_id: Template UUID.
            data: Fields to update.

        Returns:
            Updated PDFTemplate.

        Raises:
            NotFoundError: If template not found or not owned.
        """
        template = self._get_owned(user_id, template_id)

        if data.get("is_default"):
            self._clear_defaults(user_id)

        for key, value in data.items():
            setattr(template, key, value)

        self._db.commit()
        self._db.refresh(template)
        logger.info("Template updated: %s", template_id)
        return template

    def delete_template(self, user_id: uuid.UUID, template_id: uuid.UUID) -> None:
        """Delete a template.

        Args:
            user_id: Owner user UUID.
            template_id: Template UUID.

        Raises:
            NotFoundError: If template not found or not owned.
        """
        template = self._get_owned(user_id, template_id)
        self._db.delete(template)
        self._db.commit()
        logger.info("Template deleted: %s", template_id)

    def get_template(self, user_id: uuid.UUID, template_id: uuid.UUID) -> PDFTemplate:
        """Fetch a single template by ID.

        Args:
            user_id: Owner user UUID.
            template_id: Template UUID.

        Returns:
            PDFTemplate instance.

        Raises:
            NotFoundError: If not found or not owned.
        """
        return self._get_owned(user_id, template_id)

    def list_templates(self, user_id: uuid.UUID) -> list[PDFTemplate]:
        """List all templates for a user.

        Args:
            user_id: Owner user UUID.

        Returns:
            List of templates ordered by name.
        """
        return (
            self._db.query(PDFTemplate)
            .filter(PDFTemplate.created_by_id == user_id)
            .order_by(PDFTemplate.name)
            .all()
        )

    def get_default_template(self, user_id: uuid.UUID) -> PDFTemplate | None:
        """Get the user's default template, if any.

        Args:
            user_id: Owner user UUID.

        Returns:
            Default PDFTemplate or None.
        """
        return (
            self._db.query(PDFTemplate)
            .filter(PDFTemplate.created_by_id == user_id, PDFTemplate.is_default.is_(True))
            .first()
        )

    def upload_base_pdf(
        self, user_id: uuid.UUID, template_id: uuid.UUID, pdf_b64: str, filename: str
    ) -> PDFTemplate:
        """Upload a base PDF file to overlay panels onto.

        Args:
            user_id: Owner user UUID.
            template_id: Template UUID.
            pdf_b64: Base64-encoded PDF data.
            filename: Original filename.

        Returns:
            Updated PDFTemplate.
        """
        template = self._get_owned(user_id, template_id)
        template.base_pdf_data = base64.b64decode(pdf_b64)
        template.base_pdf_name = filename
        self._db.commit()
        self._db.refresh(template)
        logger.info("Base PDF uploaded for template %s: %s", template_id, filename)
        return template

    def remove_base_pdf(self, user_id: uuid.UUID, template_id: uuid.UUID) -> PDFTemplate:
        """Remove the base PDF from a template.

        Args:
            user_id: Owner user UUID.
            template_id: Template UUID.

        Returns:
            Updated PDFTemplate.
        """
        template = self._get_owned(user_id, template_id)
        template.base_pdf_data = None
        template.base_pdf_name = None
        self._db.commit()
        self._db.refresh(template)
        return template

    def _get_owned(self, user_id: uuid.UUID, template_id: uuid.UUID) -> PDFTemplate:
        """Fetch template ensuring ownership.

        Raises:
            NotFoundError: If not found or not owned by user.
        """
        template = (
            self._db.query(PDFTemplate)
            .filter(PDFTemplate.id == template_id, PDFTemplate.created_by_id == user_id)
            .first()
        )
        if template is None:
            raise NotFoundError("PDFTemplate", str(template_id))
        return template

    def _clear_defaults(self, user_id: uuid.UUID) -> None:
        """Clear is_default flag on all user templates."""
        self._db.query(PDFTemplate).filter(
            PDFTemplate.created_by_id == user_id,
            PDFTemplate.is_default.is_(True),
        ).update({"is_default": False})
