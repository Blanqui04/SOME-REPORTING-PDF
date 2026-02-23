"""Grafana proxy API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from backend.app.api.deps import get_current_user, get_grafana_client
from backend.app.models.user import User
from backend.app.schemas.grafana import DashboardDetail, DashboardSummary, PanelInfo
from backend.app.services.grafana_client import GrafanaClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grafana", tags=["grafana"])


@router.get("/dashboards", response_model=list[DashboardSummary])
def list_dashboards(
    current_user: Annotated[User, Depends(get_current_user)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
    search: str | None = None,
) -> list[DashboardSummary]:
    """List all Grafana dashboards, optionally filtered by search term.

    Args:
        current_user: Authenticated user.
        grafana: Grafana API client.
        search: Optional search query string.

    Returns:
        List of dashboard summaries.
    """
    raw_dashboards = grafana.list_dashboards(search=search)
    return [
        DashboardSummary(
            uid=d.get("uid", ""),
            title=d.get("title", ""),
            url=d.get("url", ""),
            tags=d.get("tags", []),
        )
        for d in raw_dashboards
    ]


@router.get("/dashboards/{uid}", response_model=DashboardDetail)
def get_dashboard(
    uid: str,
    current_user: Annotated[User, Depends(get_current_user)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
) -> DashboardDetail:
    """Get detailed dashboard info including all panels.

    Args:
        uid: Grafana dashboard UID.
        current_user: Authenticated user.
        grafana: Grafana API client.

    Returns:
        Dashboard detail with panel list.
    """
    data = grafana.get_dashboard(uid)
    dashboard = data.get("dashboard", {})
    meta = data.get("meta", {})

    panels = [
        PanelInfo(
            id=p["id"],
            title=p.get("title", f"Panel {p['id']}"),
            type=p.get("type", "unknown"),
        )
        for p in dashboard.get("panels", [])
        if "id" in p
    ]

    return DashboardDetail(
        uid=dashboard.get("uid", uid),
        title=dashboard.get("title", ""),
        url=meta.get("url", ""),
        tags=dashboard.get("tags", []),
        panels=panels,
    )


@router.get("/dashboards/{uid}/panels/{panel_id}/render")
def render_panel(
    uid: str,
    panel_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
    width: int = 1000,
    height: int = 500,
    from_time: str = "now-6h",
    to_time: str = "now",
) -> Response:
    """Render a single Grafana panel as a PNG image.

    Args:
        uid: Grafana dashboard UID.
        panel_id: Panel ID to render.
        current_user: Authenticated user.
        grafana: Grafana API client.
        width: Image width in pixels.
        height: Image height in pixels.
        from_time: Time range start (Grafana format).
        to_time: Time range end (Grafana format).

    Returns:
        PNG image as HTTP response.
    """
    png_bytes = grafana.render_panel(
        dashboard_uid=uid,
        panel_id=panel_id,
        width=width,
        height=height,
        from_time=from_time,
        to_time=to_time,
    )
    return Response(content=png_bytes, media_type="image/png")
