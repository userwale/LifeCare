"""
app/core/email.py – OTP email delivery service.

Delivery strategy (auto-detected from SMTP_PORT):
  - Port 465  → SMTP_SSL  (Gmail recommended)
  - Port 587  → SMTP + STARTTLS

Configure in .env:
  SMTP_HOST       = smtp.gmail.com
  SMTP_PORT       = 465
  SMTP_USERNAME   = your.email@gmail.com
  SMTP_PASSWORD   = <16-char Gmail App Password from myaccount.google.com/apppasswords>
  SMTP_FROM_EMAIL = your.email@gmail.com

Dev fallback: if SMTP_PASSWORD is empty, the OTP is printed to the console.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

_PURPOSE_LABELS: dict[str, str] = {
    "registration":   "Email Verification",
    "login":          "2-Factor Login",
    "password_reset": "Password Reset",
}


# ── HTML template ─────────────────────────────────────────────────────────────

def _html(code: str, purpose: str, expire: int) -> str:
    label = _PURPOSE_LABELS.get(purpose, purpose.replace("_", " ").title())
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>LifeCare – Verification Code</title></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:40px 16px;">
    <table width="500" cellpadding="0" cellspacing="0"
           style="background:#16171d;border-radius:16px;border:1px solid #2e303a;
                  box-shadow:0 20px 60px rgba(0,0,0,0.6);overflow:hidden;max-width:100%;">

      <!-- Header -->
      <tr><td style="padding:32px 40px 24px;text-align:center;
                     background:linear-gradient(135deg,#1a1b25,#221c30);
                     border-bottom:1px solid #2e303a;">
        <div style="font-size:40px;line-height:1;">&#9825;</div>
        <div style="font-size:24px;font-weight:700;color:#c084fc;letter-spacing:-0.5px;margin-top:6px;">
          LifeCare
        </div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;letter-spacing:1px;text-transform:uppercase;">
          Health Portal · Security
        </div>
      </td></tr>

      <!-- Body -->
      <tr><td style="padding:36px 40px 28px;">
        <p style="margin:0 0 6px;font-size:18px;font-weight:600;color:#f3f4f6;text-align:center;">
          {label}
        </p>
        <p style="margin:0 0 28px;font-size:13px;color:#9ca3af;text-align:center;line-height:1.6;">
          Enter this code to continue. It expires in
          <strong style="color:#c084fc;">{expire} minutes</strong>.
        </p>

        <!-- OTP box -->
        <div style="background:#1f2028;border:2px solid #7c3aed;border-radius:12px;
                    padding:30px 20px;text-align:center;margin-bottom:28px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:3px;
                      color:#7c3aed;text-transform:uppercase;margin-bottom:14px;">
            Your verification code
          </div>
          <div style="font-size:52px;font-weight:800;letter-spacing:14px;
                      color:#c084fc;font-family:'Courier New',monospace;line-height:1;">
            {code}
          </div>
        </div>

        <!-- Warning -->
        <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.22);
                    border-radius:8px;padding:12px 16px;text-align:center;">
          <p style="margin:0;font-size:12px;color:#fca5a5;">
            &#9888;&#65039; If you did not request this, ignore this email — your account is safe.
          </p>
        </div>
      </td></tr>

      <!-- Footer -->
      <tr><td style="padding:16px 40px 24px;text-align:center;border-top:1px solid #2e303a;">
        <p style="margin:0;font-size:11px;color:#4b5563;line-height:1.6;">
          &copy; 2026 LifeCare &nbsp;&middot;&nbsp; AI-Powered Health Portal<br/>
          This is an automated message — please do not reply.
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


def _plain(code: str, purpose: str, expire: int) -> str:
    label = _PURPOSE_LABELS.get(purpose, purpose.replace("_", " ").title())
    return (
        f"LifeCare – {label}\n"
        f"{'─' * 40}\n\n"
        f"Your one-time verification code is:\n\n"
        f"    {code}\n\n"
        f"This code expires in {expire} minutes.\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"– The LifeCare Team\n"
    )


# ── SMTP sender ───────────────────────────────────────────────────────────────

def _send_via_smtp(msg: MIMEMultipart) -> None:
    """
    Blocking SMTP send — called via asyncio.to_thread.
    Auto-selects SSL (port 465) or STARTTLS (port 587) based on SMTP_PORT.
    """
    import ssl as _ssl

    host = settings.smtp_host
    port = settings.smtp_port
    user = settings.smtp_username
    pwd  = settings.smtp_password
    ctx  = _ssl.create_default_context()

    if port == 465:
        # Direct SSL connection (Gmail recommended, verified working)
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as server:
            server.login(user, pwd)
            server.send_message(msg)
    else:
        # STARTTLS upgrade (port 587)
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(user, pwd)
            server.send_message(msg)


# ── Public API ────────────────────────────────────────────────────────────────

async def send_otp_email(email: str, code: str, purpose: str) -> None:
    """
    Send an OTP verification email.

    • If SMTP_PASSWORD is set in .env  →  real email is dispatched.
    • If SMTP_PASSWORD is empty        →  OTP is printed to the console (dev mode).
    """
    label   = _PURPOSE_LABELS.get(purpose, purpose.replace("_", " ").title())
    subject = f"LifeCare – Your {label} code: {code}"

    # ── Real SMTP delivery ────────────────────────────────────────────────────
    if settings.smtp_username and settings.smtp_password:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"LifeCare <{settings.smtp_from_email}>"
        msg["To"]      = email
        msg.attach(MIMEText(_plain(code, purpose, settings.otp_expire_minutes), "plain", "utf-8"))
        msg.attach(MIMEText(_html (code, purpose, settings.otp_expire_minutes), "html",  "utf-8"))

        try:
            await asyncio.to_thread(_send_via_smtp, msg)
            logger.info("✅ OTP email sent → %s  [%s]", email, purpose)
            return
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "❌ SMTP authentication failed for %s.\n"
                "   → Make sure SMTP_PASSWORD in .env is a Gmail App Password,\n"
                "     not your regular Google account password.\n"
                "   → Generate one at: https://myaccount.google.com/apppasswords",
                settings.smtp_username,
            )
        except smtplib.SMTPConnectError:
            logger.error(
                "❌ Could not connect to SMTP server %s:%s.\n"
                "   → Check SMTP_HOST and SMTP_PORT in .env.",
                settings.smtp_host, settings.smtp_port,
            )
        except smtplib.SMTPException as exc:
            logger.error("❌ SMTP error: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Unexpected error sending email: %s", exc)

        logger.warning("⚠️  Email sending failed — falling back to console output.")

    # ── Dev console fallback ──────────────────────────────────────────────────
    else:
        logger.warning(
            "⚠️  SMTP_PASSWORD is not set in .env — running in console simulation mode.\n"
            "   Set SMTP_PASSWORD to a Gmail App Password to send real emails."
        )

    sep = "═" * 58
    logger.warning(sep)
    logger.warning("📧  OTP CODE  [%s]", purpose.upper())
    logger.warning("To:      %s", email)
    logger.warning("Subject: %s", subject)
    logger.warning("─" * 58)
    logger.warning("Code:    %s   (expires in %d min)", code, settings.otp_expire_minutes)
    logger.warning(sep)
