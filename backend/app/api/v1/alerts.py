"""Grafana Alerting webhook endpoint.

Receives alert notifications from Grafana and triggers
automatic PDF report generation for the affected dashboard.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, get_grafana_client, get_settings
from backend.app.core.config import Settings
from backend.app.models.user import User
from backend.app.schemas.report import ReportGenerateRequest
from backend.app.services.grafana_client import GrafanaClient
from backend.app.services.report_service import ReportService
from backend.app.tasks.report_tasks import generate_report_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class GrafanaAlertLabel(BaseModel):
    """Alert label from Grafana."""

    alertname: str = ""
    grafana_folder: str = ""


class GrafanaAlertAnnotation(BaseModel):
    """Alert annotation from Grafana."""

    summary: str = ""
    description: str = ""
    dashboard_uid: str = ""


class GrafanaAlert(BaseModel):
    """Single alert entry in Grafana webhook payload."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = "firing"
    labels: GrafanaAlertLabel = GrafanaAlertLabel()
    annotations: GrafanaAlertAnnotation = GrafanaAlertAnnotation()
    dashboard_url: str = Field("", alias="dashboardURL")
    panel_url: str = Field("", alias="panelURL")
    fingerprint: str = ""


class GrafanaAlertWebhook(BaseModel):
    """Grafana Alerting webhook payload (contact point).

    Grafana sends this payload when an alert fires or resolves.
    """

    model_config = ConfigDict(populate_by_name=True)

    receiver: str = ""
    status: str = "firing"
    org_id: int = Field(1, alias="orgId")
    alerts: list[GrafanaAlert] = []
    group_labels: dict[str, str] = Field(default_factory=dict, alias="groupLabels")
    common_labels: dict[str, str] = Field(default_factory=dict, alias="commonLabels")
    common_annotations: dict[str, str] = Field(default_factory=dict, alias="commonAnnotations")
    external_url: str = Field("", alias="externalURL")
    version: str = "1"
    group_key: str = Field("", alias="groupKey")
    title: str = ""
    state: str = "alerting"
    message: str = ""


def _extract_dashboard_uid(dashboard_url: str) -> str | None:
    """Extract dashboard UID from a Grafana dashboard URL.

    Args:
        dashboard_url: Full URL like 'http://grafana:3000/d/abc123/my-dash'.

    Returns:
        Dashboard UID or None if cannot be parsed.
    """
    if not dashboard_url:
        return None
    parts = dashboard_url.split("/d/")
    if len(parts) < 2:
        return None
    uid_part = parts[1].split("/")[0].split("?")[0]
    return uid_part if uid_part else None


@router.post("/grafana-alerts", status_code=status.HTTP_202_ACCEPTED)
def receive_grafana_alert(
    payload: GrafanaAlertWebhook,
    db: Annotated[Session, Depends(get_db)],
    grafana: Annotated[GrafanaClient, Depends(get_grafana_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    """Receive a Grafana alert webhook and trigger report generation.

    Only 'firing' alerts trigger report generation. The dashboard UID
    is extracted from the alert's dashboardURL or annotations.

    Returns:
        Summary of triggered reports.
    """
    if payload.status != "firing":
        logger.info("Ignoring non-firing alert (status=%s)", payload.status)
        return {"triggered": 0, "message": "Only firing alerts trigger reports"}

    triggered_uids: set[str] = set()
    reports_created: list[str] = []

    for alert in payload.alerts:
        if alert.status != "firing":
            continue

        uid = alert.annotations.dashboard_uid or _extract_dashboard_uid(alert.dashboard_url)
        if not uid or uid in triggered_uids:
            continue
        triggered_uids.add(uid)

        try:
            dashboard_data = grafana.get_dashboard(uid)
            dashboard_title = dashboard_data.get("dashboard", {}).get("title", "Alert Report")
            all_panels = dashboard_data.get("dashboard", {}).get("panels", [])
            panel_ids = [p["id"] for p in all_panels if "id" in p]

            # Use first admin user as owner, or create a system report
            system_user = db.query(User).filter(User.role == "admin").first()
            if system_user is None:
                system_user = db.query(User).first()
            if system_user is None:
                logger.error("No users found to own alert-triggered report")
                continue

            gen_request = ReportGenerateRequest(
                dashboard_uid=uid,
                panel_ids=panel_ids,
                title=f"Alert: {alert.labels.alertname or dashboard_title}",
            )

            service = ReportService(db)
            report = service.create_report(
                user_id=system_user.id,
                request=gen_request,
                dashboard_title=dashboard_title,
            )

            template_dir = str(Path(__file__).resolve().parents[2] / "templates")
            generate_report_task.delay(
                report_id=str(report.id),
                template_dir=template_dir,
                request_params={"width": 1000, "height": 500},
            )

            reports_created.append(str(report.id))
            logger.info(
                "Alert-triggered report queued: dashboard=%s report_id=%s alert=%s",
                uid,
                report.id,
                alert.labels.alertname,
            )
        except Exception as exc:
            logger.error("Failed to create report for alert dashboard %s: %s", uid, exc)

    return {
        "triggered": len(reports_created),
        "report_ids": reports_created,
        "dashboards": list(triggered_uids),
    }
