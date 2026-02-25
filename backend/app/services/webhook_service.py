"""Webhook notification service for report completion events."""

import logging

import httpx

logger = logging.getLogger(__name__)

# Timeout for webhook HTTP calls (seconds)
_WEBHOOK_TIMEOUT = 10


class WebhookService:
    """Send HTTP POST notifications to configured webhook URLs.

    Used to notify external systems when a scheduled report
    generation completes or fails.
    """

    @staticmethod
    def notify(
        webhook_url: str,
        payload: dict,
    ) -> bool:
        """Send a POST request with JSON payload to the webhook URL.

        Args:
            webhook_url: Target URL for the notification.
            payload: JSON-serializable dictionary to send.

        Returns:
            True if the webhook responded with 2xx, False otherwise.
        """
        try:
            response = httpx.post(
                webhook_url,
                json=payload,
                timeout=_WEBHOOK_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            if response.is_success:
                logger.info("Webhook sent to %s (status=%d)", webhook_url, response.status_code)
                return True
            else:
                logger.warning(
                    "Webhook to %s failed (status=%d): %s",
                    webhook_url,
                    response.status_code,
                    response.text[:200],
                )
                return False

        except Exception as e:
            logger.error("Webhook to %s failed: %s", webhook_url, e, exc_info=True)
            return False
