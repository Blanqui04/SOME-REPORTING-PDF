"""Report request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportGenerateRequest(BaseModel):
    """Schema for requesting a new report generation.

    Attributes:
        dashboard_uid: Grafana dashboard UID to generate report from.
        panel_ids: List of panel IDs to include in the report.
        title: Custom report title (auto-generated from dashboard if omitted).
        description: Optional report description.
        time_range_from: Grafana time range start (e.g. 'now-6h').
        time_range_to: Grafana time range end (e.g. 'now').
        width: Panel image width in pixels.
        height: Panel image height in pixels.
    """

    dashboard_uid: str = Field(..., min_length=1, max_length=100)
    panel_ids: list[int] = Field(..., min_length=1)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    time_range_from: str = Field(default="now-6h")
    time_range_to: str = Field(default="now")
    width: int = Field(default=1000, ge=100, le=4000)
    height: int = Field(default=500, ge=100, le=4000)


class ReportResponse(BaseModel):
    """Schema for report metadata responses (PDF binary excluded).

    Attributes:
        id: Report UUID.
        title: Report title.
        description: Optional description.
        dashboard_uid: Source Grafana dashboard UID.
        dashboard_title: Dashboard title at generation time.
        panel_ids: List of included panel IDs.
        time_range_from: Time range start.
        time_range_to: Time range end.
        status: Generation status (pending/generating/completed/failed).
        pdf_size_bytes: Size of the generated PDF in bytes.
        file_name: Generated PDF filename.
        error_message: Error details if generation failed.
        created_by_id: UUID of the user who created the report.
        generated_at: Timestamp when PDF generation completed.
        created_at: Report creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    title: str
    description: str | None
    dashboard_uid: str
    dashboard_title: str
    panel_ids: list[int]
    time_range_from: str | None
    time_range_to: str | None
    status: str
    pdf_size_bytes: int | None
    file_name: str
    error_message: str | None
    created_by_id: uuid.UUID
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
