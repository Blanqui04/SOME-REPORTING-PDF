"""Email service for sending PDF reports via SMTP."""

import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailService:
    """Send PDF report attachments via SMTP.

    Args:
        settings: Application settings with SMTP configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_report(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        pdf_data: bytes,
        pdf_filename: str,
    ) -> bool:
        """Send a PDF report as an email attachment.

        Args:
            recipients: List of email addresses.
            subject: Email subject line.
            body: Email body text (plain text).
            pdf_data: PDF file bytes.
            pdf_filename: Filename for the attachment.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self._settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email send")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self._settings.SMTP_FROM_EMAIL
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            # Attach PDF
            attachment = MIMEBase("application", "pdf")
            attachment.set_payload(pdf_data)
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f'attachment; filename="{pdf_filename}"',
            )
            msg.attach(attachment)

            # Connect and send
            with smtplib.SMTP(self._settings.SMTP_HOST, self._settings.SMTP_PORT) as server:
                if self._settings.SMTP_TLS:
                    server.starttls()
                if self._settings.SMTP_USER and self._settings.SMTP_PASSWORD:
                    server.login(self._settings.SMTP_USER, self._settings.SMTP_PASSWORD)
                server.sendmail(
                    self._settings.SMTP_FROM_EMAIL,
                    recipients,
                    msg.as_string(),
                )

            logger.info("Email sent to %s: %s", recipients, subject)
            return True

        except Exception as e:
            logger.error("Failed to send email to %s: %s", recipients, e, exc_info=True)
            return False
