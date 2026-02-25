"""Report request and response schemas."""

import uuid
from datetime import datetime
from typing import Literal

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
        template_id: PDF template UUID for branding.
        language: Language for PDF labels.
        orientation: Page orientation (portrait or landscape).
        toc_enabled: Whether to include a Table of Contents.
        watermark_text: Diagonal watermark text (e.g. 'Confidential').
        panel_columns: Number of panel columns (1=full width, 2=side by side).
        include_data_tables: Whether to include raw data tables as annex.
        comparison_time_from: Comparison period B start (enables comparison mode).
        comparison_time_to: Comparison period B end.
    """

    dashboard_uid: str = Field(..., min_length=1, max_length=100)
    panel_ids: list[int] = Field(..., min_length=1)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    time_range_from: str = Field(default="now-6h")
    time_range_to: str = Field(default="now")
    width: int = Field(default=1000, ge=100, le=4000)
    height: int = Field(default=500, ge=100, le=4000)
    template_id: str | None = Field(default=None, description="PDF template UUID to use for branding")
    language: Literal["ca", "es", "en", "pl"] = Field(
        default="ca",
        description="Language for PDF labels: ca (Catalan), es (Spanish), en (English), pl (Polish)",
    )
    # Sprint 5: PDF engine enhancements
    orientation: Literal["portrait", "landscape"] = Field(
        default="portrait",
        description="Page orientation: portrait or landscape",
    )
    toc_enabled: bool = Field(
        default=False,
        description="Include Table of Contents page with panel links",
    )
    watermark_text: str | None = Field(
        default=None,
        max_length=100,
        description="Diagonal watermark text (e.g. 'Confidential', 'Draft')",
    )
    panel_columns: int = Field(
        default=1,
        ge=1,
        le=2,
        description="Panel grid columns: 1 (full width) or 2 (side by side)",
    )
    include_data_tables: bool = Field(
        default=False,
        description="Include raw panel data as table annex in PDF",
    )
    comparison_time_from: str | None = Field(
        default=None,
        description="Comparison period B start (enables temporal comparison mode)",
    )
    comparison_time_to: str | None = Field(
        default=None,
        description="Comparison period B end",
    )


class BatchGenerateRequest(BaseModel):
    """Schema for batch report generation across multiple dashboards.

    Attributes:
        dashboard_uids: List of dashboard UIDs to generate reports for.
        panel_ids: Panel IDs to include (applied to all dashboards).
        time_range_from: Grafana time range start.
        time_range_to: Grafana time range end.
        language: Language for PDF labels.
        orientation: Page orientation.
    """

    dashboard_uids: list[str] = Field(..., min_length=1, max_length=50)
    panel_ids: list[int] = Field(default_factory=list)
    time_range_from: str = Field(default="now-6h")
    time_range_to: str = Field(default="now")
    width: int = Field(default=1000, ge=100, le=4000)
    height: int = Field(default=500, ge=100, le=4000)
    language: Literal["ca", "es", "en", "pl"] = Field(default="ca")
    orientation: Literal["portrait", "landscape"] = Field(default="portrait")


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
