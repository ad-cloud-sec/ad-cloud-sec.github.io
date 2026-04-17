#!/usr/bin/env python3
"""
Gmail sender for CyberSec Intelligence Dashboard.

Sends the generated HTML dashboard as an inline HTML email
with the file also attached, using Gmail SMTP + App Password.

Required .env variables:
    GMAIL_ADDRESS      — your Gmail address (sender & default recipient)
    GMAIL_APP_PASSWORD — Gmail App Password (not your account password)

Optional .env variables:
    GMAIL_RECIPIENT    — recipient address (defaults to GMAIL_ADDRESS)
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

logger = logging.getLogger("dashboard.gmail")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_dashboard_email(html_path: Path) -> bool:
    """
    Send the dashboard HTML to Gmail.

    Args:
        html_path: Path to the generated dashboard HTML file.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    sender = os.getenv("GMAIL_ADDRESS", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.getenv("GMAIL_RECIPIENT", "").strip() or sender

    if not sender or not app_password:
        logger.warning(
            "Gmail not configured — set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env "
            "to enable email delivery."
        )
        return False

    if not html_path.exists():
        logger.error("Dashboard HTML not found at %s — cannot send email.", html_path)
        return False

    html_content = html_path.read_text(encoding="utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"CyberSec Intelligence Dashboard — {timestamp}"

    # ── Build the email ────────────────────────────────────────────────────────
    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    # 1. Inline HTML body
    body = MIMEMultipart("alternative")
    plain_text = (
        f"CyberSec Intelligence Dashboard — {timestamp}\n\n"
        "Open the attached dashboard.html file or enable HTML rendering to view this report."
    )
    body.attach(MIMEText(plain_text, "plain", "utf-8"))
    body.attach(MIMEText(html_content, "html", "utf-8"))
    msg.attach(body)

    # 2. HTML file attachment
    attachment = MIMEBase("text", "html")
    attachment.set_payload(html_content.encode("utf-8"))
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"cybersec_dashboard_{datetime.now().strftime('%Y-%m-%d_%H%M')}.html",
    )
    msg.attach(attachment)

    # ── Send via Gmail SMTP ────────────────────────────────────────────────────
    try:
        logger.info("Connecting to Gmail SMTP (%s:%d) …", SMTP_HOST, SMTP_PORT)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(sender, app_password)
            smtp.sendmail(sender, recipient, msg.as_string())
        logger.info("Dashboard emailed to %s ✓", recipient)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. Make sure you are using an App Password, "
            "not your account password. Generate one at: "
            "Google Account → Security → 2-Step Verification → App Passwords"
        )
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending email: %s", exc)
    except OSError as exc:
        logger.error("Network error while connecting to Gmail: %s", exc)

    return False
