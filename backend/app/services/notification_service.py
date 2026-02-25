"""Webhook notification service for Slack and Microsoft Teams.

Sends PDF report status notifications to configured webhook URLs.
Supports both Slack Incoming Webhooks and Microsoft Teams connectors.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10


class WebhookType(StrEnum):
    """Supported webhook platforms."""

    SLACK = "slack"
    TEAMS = "teams"
    GENERIC = "generic"


class NotificationService:
    """Send report lifecycle notifications to external webhooks.

    Args:
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, timeout: int = _TIMEOUT) -> None:
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify_report_completed(
        self,
        webhook_url: str,
        webhook_type: WebhookType,
        report_title: str,
        dashboard_title: str,
        download_url: str = "",
        file_size_bytes: int = 0,
    ) -> bool:
        """Send a 'report completed' notification.

        Args:
            webhook_url: Full URL of the incoming webhook.
            webhook_type: Platform type (slack, teams, generic).
            report_title: Title of the generated report.
            dashboard_title: Grafana dashboard title.
            download_url: Optional direct download link.
            file_size_bytes: PDF file size in bytes.

        Returns:
            True if the notification was delivered successfully.
        """
        payload = self._build_payload(
            webhook_type=webhook_type,
            status="completed",
            report_title=report_title,
            dashboard_title=dashboard_title,
            download_url=download_url,
            file_size_bytes=file_size_bytes,
        )
        return self._send(webhook_url, payload)

    def notify_report_failed(
        self,
        webhook_url: str,
        webhook_type: WebhookType,
        report_title: str,
        dashboard_title: str,
        error_message: str = "",
    ) -> bool:
        """Send a 'report failed' notification.

        Args:
            webhook_url: Full URL of the incoming webhook.
            webhook_type: Platform type (slack, teams, generic).
            report_title: Title of the report.
            dashboard_title: Grafana dashboard title.
            error_message: Error description.

        Returns:
            True if the notification was delivered successfully.
        """
        payload = self._build_payload(
            webhook_type=webhook_type,
            status="failed",
            report_title=report_title,
            dashboard_title=dashboard_title,
            error_message=error_message,
        )
        return self._send(webhook_url, payload)

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        *,
        webhook_type: WebhookType,
        status: str,
        report_title: str,
        dashboard_title: str,
        download_url: str = "",
        file_size_bytes: int = 0,
        error_message: str = "",
    ) -> dict[str, Any]:
        """Build platform-specific JSON payload."""
        if webhook_type == WebhookType.SLACK:
            return self._slack_payload(
                status, report_title, dashboard_title,
                download_url, file_size_bytes, error_message,
            )
        if webhook_type == WebhookType.TEAMS:
            return self._teams_payload(
                status, report_title, dashboard_title,
                download_url, file_size_bytes, error_message,
            )
        return self._generic_payload(
            status, report_title, dashboard_title,
            download_url, file_size_bytes, error_message,
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Human-readable file size."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _slack_payload(
        self,
        status: str,
        report_title: str,
        dashboard_title: str,
        download_url: str,
        file_size_bytes: int,
        error_message: str,
    ) -> dict[str, Any]:
        """Build a Slack Block Kit message."""
        icon = ":white_check_mark:" if status == "completed" else ":x:"
        colour = "#36a64f" if status == "completed" else "#dc3545"
        title_text = f"{icon} Report *{status.upper()}*: {report_title}"

        fields = [
            {"type": "mrkdwn", "text": f"*Dashboard:*\n{dashboard_title}"},
        ]
        if status == "completed" and file_size_bytes:
            fields.append(
                {"type": "mrkdwn", "text": f"*Size:*\n{self._format_size(file_size_bytes)}"},
            )
        if error_message:
            fields.append({"type": "mrkdwn", "text": f"*Error:*\n{error_message}"})

        blocks: list[dict[str, Any]] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": title_text}},
            {"type": "section", "fields": fields},
        ]

        if download_url and status == "completed":
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": ":arrow_down: Download PDF"},
                        "url": download_url,
                        "style": "primary",
                    },
                ],
            })

        return {
            "attachments": [{"color": colour, "blocks": blocks}],
        }

    def _teams_payload(
        self,
        status: str,
        report_title: str,
        dashboard_title: str,
        download_url: str,
        file_size_bytes: int,
        error_message: str,
    ) -> dict[str, Any]:
        """Build a Microsoft Teams Adaptive Card payload."""
        icon = "\u2705" if status == "completed" else "\u274c"
        colour = "good" if status == "completed" else "attention"

        facts = [
            {"name": "Dashboard", "value": dashboard_title},
            {"name": "Status", "value": status.upper()},
        ]
        if file_size_bytes:
            facts.append({"name": "Size", "value": self._format_size(file_size_bytes)})
        if error_message:
            facts.append({"name": "Error", "value": error_message})

        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "size": "medium",
                "weight": "bolder",
                "text": f"{icon} Report {status.upper()}: {report_title}",
                "color": colour,
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ]

        actions: list[dict[str, Any]] = []
        if download_url and status == "completed":
            actions.append({
                "type": "Action.OpenUrl",
                "title": "Download PDF",
                "url": download_url,
            })

        card: dict[str, Any] = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body,
                        "actions": actions,
                    },
                },
            ],
        }
        return card

    @staticmethod
    def _generic_payload(
        status: str,
        report_title: str,
        dashboard_title: str,
        download_url: str,
        file_size_bytes: int,
        error_message: str,
    ) -> dict[str, Any]:
        """Build a simple JSON payload for generic webhooks."""
        return {
            "event": f"report.{status}",
            "report_title": report_title,
            "dashboard_title": dashboard_title,
            "status": status,
            "download_url": download_url,
            "file_size_bytes": file_size_bytes,
            "error_message": error_message,
        }

    # ------------------------------------------------------------------
    # HTTP delivery
    # ------------------------------------------------------------------

    def _send(self, url: str, payload: dict[str, Any]) -> bool:
        """POST the payload to the webhook URL.

        Returns:
            True on success (2xx), False otherwise.
        """
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
            if response.is_success:
                logger.info("Webhook notification sent to %s", url)
                return True
            logger.warning(
                "Webhook returned %s from %s: %s",
                response.status_code, url, response.text[:200],
            )
        except httpx.HTTPError as exc:
            logger.error("Webhook delivery failed for %s: %s", url, exc)
        return False
