"""SMTP delivery for one-time email-verification codes."""

from __future__ import annotations

import asyncio
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings
from app.core.logging import logger


class OtpDeliveryError(RuntimeError):
    """Raised when the verification code could not be sent after storage."""


class OtpSender(Protocol):
    """The minimal delivery boundary used by registration services and tests."""

    async def send_verification_code(
        self,
        *,
        recipient: str,
        otp: str,
        expires_at: datetime,
    ) -> None:
        """Deliver a one-time email-verification code."""


class SmtpOtpSender:
    """Send codes through Mailpit locally and SMTP infrastructure in production."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._sender = settings.smtp_from

    async def send_verification_code(
        self,
        *,
        recipient: str,
        otp: str,
        expires_at: datetime,
    ) -> None:
        try:
            await asyncio.to_thread(
                self._send,
                recipient=recipient,
                otp=otp,
                expires_at=expires_at,
            )
        except (OSError, smtplib.SMTPException) as error:
            logger.warning(
                "registration OTP delivery failed",
                extra={
                    "event": "registration_otp_delivery_failed",
                    "context": {"errorType": type(error).__name__},
                },
            )
            raise OtpDeliveryError("OTP delivery failed.") from error

    def _send(self, *, recipient: str, otp: str, expires_at: datetime) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = "Verify your FoC email address"
        message.set_content(
            f"Your FoC verification code is {otp}. "
            f"It expires at {expires_at.isoformat()}. Do not share this code."
        )
        with smtplib.SMTP(self._host, self._port, timeout=10) as client:
            client.send_message(message)
