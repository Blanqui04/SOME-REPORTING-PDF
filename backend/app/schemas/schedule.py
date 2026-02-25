"""Schedule request and response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreateRequest(BaseModel):
    """Schema for creating a new scheduled report.

    Attributes:
        name: Human-readable schedule name.
        dashboard_uid: Grafana dashboard UID to generate report from.
        panel_ids: List of panel IDs to include in the report.
        cron_expression: Cron expression for scheduling (e.g. '0 8 * * 1').
        time_range_from: Grafana time range start (e.g. 'now-24h').
        time_range_to: Grafana time range end (e.g. 'now').
        email_recipients: List of email addresses to send the report to.
        webhook_url: URL to POST a notification when report is ready.
        language: Language for PDF labels.
        template_id: Optional PDF template UUID.
        width: Panel image width in pixels.
        height: Panel image height in pixels.
        description: Optional description.
    """

    name: str = Field(..., min_length=1, max_length=255)
    dashboard_uid: str = Field(..., min_length=1, max_length=100)
    panel_ids: list[int] = Field(..., min_length=1)
    cron_expression: str = Field(..., min_length=1, max_length=100)
    time_range_from: str = Field(default="now-24h")
    time_range_to: str = Field(default="now")
    email_recipients: list[str] | None = Field(default=None)
    webhook_url: str | None = Field(default=None, max_length=2048)
    language: Literal["ca", "es", "en", "pl"] = Field(default="ca")
    template_id: str | None = Field(default=None)
    width: int = Field(default=1000, ge=100, le=4000)
    height: int = Field(default=500, ge=100, le=4000)
    description: str | None = None


class ScheduleUpdateRequest(BaseModel):
    """Schema for updating a scheduled report.

    All fields are optional — only provided fields are updated.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    panel_ids: list[int] | None = Field(default=None, min_length=1)
    cron_expression: str | None = Field(default=None, min_length=1, max_length=100)
    time_range_from: str | None = None
    time_range_to: str | None = None
    email_recipients: list[str] | None = None
    webhook_url: str | None = Field(default=None, max_length=2048)
    is_active: bool | None = None
    language: Literal["ca", "es", "en", "pl"] | None = None
    template_id: str | None = None
    width: int | None = Field(default=None, ge=100, le=4000)
    height: int | None = Field(default=None, ge=100, le=4000)
    description: str | None = None


class ScheduleResponse(BaseModel):
    """Schema for schedule responses.

    Attributes:
        id: Schedule UUID.
        name: Schedule name.
        dashboard_uid: Source Grafana dashboard UID.
        dashboard_title: Dashboard title.
        panel_ids: Included panel IDs.
        cron_expression: Cron expression.
        time_range_from: Time range start.
        time_range_to: Time range end.
        is_active: Whether the schedule is active.
        email_recipients: Email addresses for delivery.
        webhook_url: Webhook notification URL.
        language: PDF language.
        template_id: PDF template UUID.
        width: Panel render width.
        height: Panel render height.
        description: Optional description.
        last_run_at: Last execution time.
        next_run_at: Next scheduled execution time.
        user_id: Owner user UUID.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    name: str
    dashboard_uid: str
    dashboard_title: str | None
    panel_ids: list[int]
    cron_expression: str
    time_range_from: str | None
    time_range_to: str | None
    is_active: bool
    email_recipients: list[str] | None
    webhook_url: str | None
    language: str
    template_id: str | None
    width: int
    height: int
    description: str | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
