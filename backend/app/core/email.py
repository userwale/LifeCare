"""
app/core/email.py – Service to send OTP emails.
Supports real SMTP sending and console logs fallback in development.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


async def send_otp_email(email: str, code: str, purpose: str) -> None:
    """
    Sends an OTP verification email to the user.
    If SMTP credentials are not configured, it logs the OTP code to the console.
    """
    subject = f"LifeCare - OTP Code for {purpose.replace('_', ' ').title()}"
    body = (
        f"Hello,\n\n"
        f"Your One-Time Password (OTP) for {purpose.replace('_', ' ')} is: {code}\n\n"
        f"This code will expire in {settings.otp_expire_minutes} minutes.\n\n"
        f"If you did not request this code, you can safely ignore this email.\n\n"
        f"Best regards,\n"
        f"The LifeCare Team\n"
    )

    # If SMTP is configured, attempt sending email
    if settings.smtp_username and settings.smtp_password:
        try:
            def send_sync():
                msg = MIMEText(body)
                msg["Subject"] = subject
                msg["From"] = settings.smtp_from_email
                msg["To"] = email

                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    server.login(settings.smtp_username, settings.smtp_password)
                    server.send_message(msg)

            await asyncio.to_thread(send_sync)
            logger.info("📧 Sent OTP email successfully to %s", email)
            return
        except Exception as e:
            logger.error("❌ Failed to send OTP email via SMTP: %s", e)
            logger.info("ℹ️ Falling back to console simulation.")

    # Simulated email output for development
    logger.warning("==================================================")
    logger.warning("📧 [DEV EMAIL SIMULATION]")
    logger.warning("To:      %s", email)
    logger.warning("Subject: %s", subject)
    logger.warning("--------------------------------------------------")
    logger.warning("Body:\n%s", body.strip())
    logger.warning("==================================================")
