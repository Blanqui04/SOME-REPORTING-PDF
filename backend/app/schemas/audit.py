"""Audit log response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Schema for audit log entry responses.

    Attributes:
        id: Audit log entry UUID.
        user_id: User who performed the action.
        action: Action type.
        resource_type: Resource type affected.
        resource_id: Resource UUID.
        details: Human-readable description.
        ip_address: Client IP.
        user_agent: Client user agent.
        metadata_json: Additional metadata.
        created_at: Entry timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: str | None
    ip_address: str | None
    user_agent: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
