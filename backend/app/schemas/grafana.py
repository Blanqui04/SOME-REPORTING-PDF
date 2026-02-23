"""Grafana API response schemas."""

from pydantic import BaseModel


class PanelInfo(BaseModel):
    """Minimal panel information from a Grafana dashboard.

    Attributes:
        id: Grafana panel ID.
        title: Panel display title.
        type: Panel type (e.g. 'graph', 'table', 'stat').
    """

    id: int
    title: str
    type: str


class DashboardSummary(BaseModel):
    """Brief dashboard info from Grafana search API.

    Attributes:
        uid: Dashboard unique identifier.
        title: Dashboard display title.
        url: Relative URL path in Grafana.
        tags: List of dashboard tags.
    """

    uid: str
    title: str
    url: str
    tags: list[str] = []


class DashboardDetail(BaseModel):
    """Full dashboard info including panel list.

    Attributes:
        uid: Dashboard unique identifier.
        title: Dashboard display title.
        url: Relative URL path in Grafana.
        tags: List of dashboard tags.
        panels: List of panels in the dashboard.
    """

    uid: str
    title: str
    url: str
    tags: list[str] = []
    panels: list[PanelInfo] = []
