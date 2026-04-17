#!/usr/bin/env python3
"""
Gmail sender for CyberSec Intelligence Dashboard.

Sends a professional HTML digest email (executive summary with top stories,
severity stats, and THREATCON level) with the full dashboard attached.

Required env variables:
    GMAIL_ADDRESS      — sender Gmail address
    GMAIL_APP_PASSWORD — Gmail App Password (not your account password)

Optional env variables:
    GMAIL_RECIPIENT    — recipient address (defaults to GMAIL_ADDRESS)
    DASHBOARD_URL      — public URL to link to (e.g. GitHub Pages URL)
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

logger = logging.getLogger("dashboard.gmail")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

_SEV_RANK = {"Critical": 0, "High": 1, "Interesting": 2}


def send_dashboard_email(html_path: Path, data: dict | None = None) -> bool:
    sender       = os.getenv("GMAIL_ADDRESS", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient    = os.getenv("GMAIL_RECIPIENT", "").strip() or sender
    dashboard_url = os.getenv("DASHBOARD_URL", "").strip()

    if not sender or not app_password:
        logger.warning(
            "Gmail not configured — set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env."
        )
        return False

    if not html_path.exists():
        logger.error("Dashboard HTML not found at %s — cannot send email.", html_path)
        return False

    now       = datetime.now(timezone.utc)
    date_str  = now.strftime("%d %b %Y")
    time_str  = now.strftime("%H:%M UTC")
    subject   = f"[AD-SEC INTEL] Cybersecurity Intelligence Brief — {date_str}"

    email_body = _build_email_html(data or {}, date_str, time_str, dashboard_url)

    msg = MIMEMultipart("mixed")
    msg["From"]    = sender
    msg["To"]      = recipient
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(_build_plain_text(data or {}, date_str), "plain", "utf-8"))
    alt.attach(MIMEText(email_body, "html", "utf-8"))
    msg.attach(alt)

    attachment = MIMEBase("text", "html")
    attachment.set_payload(html_path.read_bytes())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"ad-sec-intel_{now.strftime('%Y-%m-%d_%H%M')}.html",
    )
    msg.attach(attachment)

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
            "Gmail authentication failed. Use an App Password from: "
            "Google Account → Security → 2-Step Verification → App Passwords"
        )
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
    except OSError as exc:
        logger.error("Network error connecting to Gmail: %s", exc)

    return False


# ── Email content builders ─────────────────────────────────────────────────────

def _build_plain_text(data: dict, date_str: str) -> str:
    categories   = data.get("categories", {})
    total_shown  = data.get("total_shown", 0)
    critical_n   = sum(1 for items in categories.values() for i in items if i.get("severity") == "Critical")
    high_n       = sum(1 for items in categories.values() for i in items if i.get("severity") == "High")

    lines = [
        f"AD-SEC INTEL — Cybersecurity Intelligence Brief — {date_str}",
        "=" * 60,
        f"Critical: {critical_n}  |  High: {high_n}  |  Total stories: {total_shown}",
        "",
        "Top stories attached in full dashboard HTML.",
        "",
        "Sources: NVD CVE API · CISA KEV · 30+ RSS feeds · GitHub Trending",
        "For security research and awareness only.",
    ]
    return "\n".join(lines)


def _build_email_html(data: dict, date_str: str, time_str: str, dashboard_url: str) -> str:
    categories    = data.get("categories", {})
    total_shown   = data.get("total_shown", 0)
    total_raw     = data.get("total_raw", 0)
    critical_n    = sum(1 for items in categories.values() for i in items if i.get("severity") == "Critical")
    high_n        = sum(1 for items in categories.values() for i in items if i.get("severity") == "High")

    tc_level, tc_color, tc_desc = _threatcon(critical_n, high_n)

    top_stories = _pick_top_stories(categories, n=5)
    stories_html = "".join(_story_row(s) for s in top_stories)

    cta_html = ""
    if dashboard_url:
        cta_html = f"""
        <tr><td style="padding:0 32px 28px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center">
              <a href="{dashboard_url}"
                 style="display:inline-block;background:#00c896;color:#07090f;font-family:monospace;
                        font-size:13px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;
                        padding:12px 32px;border-radius:6px;text-decoration:none;">
                VIEW FULL DASHBOARD →
              </a>
            </td></tr>
          </table>
        </td></tr>"""
    else:
        cta_html = """
        <tr><td style="padding:0 32px 28px;">
          <p style="margin:0;font-size:12px;color:#5a7290;text-align:center;">
            Full interactive dashboard is attached to this email.
          </p>
        </td></tr>"""

    cat_rows = _category_breakdown(categories)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>AD-SEC INTEL — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#07090f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#07090f;max-width:680px;margin:0 auto;">

  <!-- ── Header ── -->
  <tr>
    <td style="background:#0d1117;padding:20px 32px 18px;border-bottom:2px solid #00c896;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <span style="font-family:monospace;font-size:17px;font-weight:800;color:#00c896;letter-spacing:.08em;">⬡ AD-SEC INTEL</span>
            <br>
            <span style="font-size:11px;color:#5a7290;letter-spacing:.05em;text-transform:uppercase;">Cybersecurity Intelligence</span>
          </td>
          <td align="right" style="vertical-align:top;">
            <span style="font-family:monospace;font-size:11px;color:#5a7290;">{date_str}</span>
            <br>
            <span style="font-family:monospace;font-size:11px;color:#3a5270;">{time_str}</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── THREATCON banner ── -->
  <tr>
    <td style="background:rgba(0,0,0,0.3);padding:10px 32px;border-bottom:1px solid {tc_color}40;">
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding-right:10px;">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{tc_color};"></span>
          </td>
          <td>
            <span style="font-family:monospace;font-size:10px;font-weight:800;letter-spacing:.1em;color:{tc_color};
                         background:{tc_color}1a;border:1px solid {tc_color}40;border-radius:3px;padding:2px 7px;">
              THREATCON
            </span>
            <span style="font-family:monospace;font-size:12px;font-weight:800;color:{tc_color};margin-left:6px;">{tc_level}</span>
            <span style="font-size:12px;color:#8ba3c4;margin-left:8px;">— {tc_desc}</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── Stats row ── -->
  <tr>
    <td style="padding:20px 32px 16px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="32%" align="center"
              style="background:#16101a;border:1px solid #f43f5e40;border-radius:8px;padding:16px 8px;">
            <div style="font-size:30px;font-weight:800;color:#f43f5e;font-family:monospace;line-height:1;">{critical_n}</div>
            <div style="font-size:10px;color:#8ba3c4;text-transform:uppercase;letter-spacing:.08em;margin-top:5px;">Critical</div>
          </td>
          <td width="4%"></td>
          <td width="32%" align="center"
              style="background:#16120e;border:1px solid #f9731640;border-radius:8px;padding:16px 8px;">
            <div style="font-size:30px;font-weight:800;color:#f97316;font-family:monospace;line-height:1;">{high_n}</div>
            <div style="font-size:10px;color:#8ba3c4;text-transform:uppercase;letter-spacing:.08em;margin-top:5px;">High</div>
          </td>
          <td width="4%"></td>
          <td width="32%" align="center"
              style="background:#0d1117;border:1px solid #ffffff14;border-radius:8px;padding:16px 8px;">
            <div style="font-size:30px;font-weight:800;color:#eef4ff;font-family:monospace;line-height:1;">{total_shown}</div>
            <div style="font-size:10px;color:#8ba3c4;text-transform:uppercase;letter-spacing:.08em;margin-top:5px;">Stories</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── Top stories heading ── -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-top:1px solid #ffffff0d;padding-top:16px;">
        <tr>
          <td>
            <span style="font-family:monospace;font-size:10px;font-weight:700;letter-spacing:.1em;color:#f43f5e;">● LIVE</span>
            <span style="font-size:14px;font-weight:700;color:#eef4ff;margin-left:10px;">Today's Lead Stories</span>
          </td>
          <td align="right">
            <span style="font-size:10px;color:#3a5270;">{total_raw} items aggregated</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── Story rows ── -->
  <tr>
    <td style="padding:0 32px;">
      <table width="100%" cellpadding="0" cellspacing="0">
{stories_html}
      </table>
    </td>
  </tr>

  <!-- ── Category breakdown ── -->
  <tr>
    <td style="padding:20px 32px 8px;">
      <p style="margin:0 0 10px;font-size:11px;font-weight:700;color:#5a7290;text-transform:uppercase;letter-spacing:.08em;">
        Coverage by Category
      </p>
      <table width="100%" cellpadding="0" cellspacing="0">
{cat_rows}
      </table>
    </td>
  </tr>

  <!-- ── CTA ── -->
{cta_html}

  <!-- ── Footer ── -->
  <tr>
    <td style="border-top:1px solid #ffffff0d;padding:16px 32px;background:#0d1117;">
      <p style="margin:0;font-size:11px;color:#3a5270;line-height:1.6;">
        <span style="font-family:monospace;font-weight:700;color:#00c896;">AD-SEC INTEL</span>
        &nbsp;·&nbsp; NVD CVE API · CISA KEV · 30+ RSS feeds · GitHub Trending
        <br>For security research and awareness only. Not for redistribution.
      </p>
    </td>
  </tr>

</table>
</body>
</html>"""


def _threatcon(critical_n: int, high_n: int) -> tuple:
    if critical_n > 0:
        return ("CRITICAL", "#f43f5e",
                f"{critical_n} critical {'advisory' if critical_n == 1 else 'advisories'} — immediate review recommended")
    elif high_n >= 3:
        return ("HIGH", "#f97316", f"{high_n} high-severity threats identified today")
    elif high_n > 0:
        return ("ELEVATED", "#eab308", "Elevated threat activity — monitor high-severity items")
    return ("NORMAL", "#00c896", "Standard threat environment — no critical advisories")


def _pick_top_stories(categories: dict, n: int = 5) -> list:
    priority = ["cve_vuln", "threat_intel", "ai_llm_security", "offensive_defensive", "cloud_security", "new_notable"]
    seen, stories = set(), []
    for cat in priority:
        for item in sorted(categories.get(cat, []),
                           key=lambda i: (_SEV_RANK.get(i.get("severity", "Interesting"), 2),
                                          -(i.get("published_dt").timestamp() if i.get("published_dt") else 0))):
            url = item.get("url")
            if url and url not in seen:
                seen.add(url)
                stories.append((cat, item))
                break
        if len(stories) >= n:
            break
    return stories


_CAT_LABEL = {
    "cve_vuln":            ("CVEs & Vulnerabilities", "#f43f5e"),
    "cloud_security":      ("Cloud Security",         "#0ea5e9"),
    "ai_llm_security":     ("AI / LLM Security",      "#a855f7"),
    "threat_intel":        ("Threat Intelligence",    "#f97316"),
    "offensive_defensive": ("Offensive & Defensive",  "#10b981"),
    "product_launches":    ("Product Launches",       "#eab308"),
    "new_notable":         ("New & Notable",          "#ec4899"),
}


def _story_row(story: tuple) -> str:
    cat_key, item = story
    label, color  = _CAT_LABEL.get(cat_key, ("Intel", "#00c896"))
    title  = (item.get("title") or "Untitled")[:120]
    source = item.get("source", "")
    sev    = item.get("severity") or "Info"
    url    = item.get("url", "#")
    cvss   = item.get("cvss")
    kev    = item.get("kev", False)

    sev_color = {"Critical": "#f43f5e", "High": "#f97316"}.get(sev, "#5a7290")
    sev_bg    = {"Critical": "#f43f5e1a", "High": "#f973161a"}.get(sev, "#ffffff0a")

    badges = f'<span style="font-family:monospace;font-size:9px;font-weight:700;color:{sev_color};background:{sev_bg};border:1px solid {sev_color}40;border-radius:3px;padding:1px 6px;">{sev.upper()}</span>'
    if cvss:
        badges += f' <span style="font-family:monospace;font-size:9px;font-weight:700;color:#fde68a;background:#eab30820;border:1px solid #eab30840;border-radius:3px;padding:1px 6px;">CVSS {cvss:.1f}</span>'
    if kev:
        badges += ' <span style="font-family:monospace;font-size:9px;font-weight:800;color:#fca5a5;background:#f43f5e20;border:1px solid #f43f5e50;border-radius:3px;padding:1px 6px;">KEV ⚑</span>'

    return f"""        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #ffffff08;">
            <div style="margin-bottom:5px;">
              <span style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:{color};
                           background:{color}14;border:1px solid {color}30;border-radius:3px;padding:1px 6px;">{label}</span>
              &nbsp;{badges}
            </div>
            <a href="{url}" style="font-size:13px;font-weight:600;color:#d4e4f7;text-decoration:none;line-height:1.45;">{title}</a>
            <div style="margin-top:4px;font-size:11px;color:#3a5270;">via {source}</div>
          </td>
        </tr>"""


def _category_breakdown(categories: dict) -> str:
    rows = []
    for cat_key, (label, color) in _CAT_LABEL.items():
        count = len(categories.get(cat_key, []))
        if count == 0:
            continue
        pct   = min(count * 4, 100)
        rows.append(f"""        <tr>
          <td width="34%" style="padding:3px 0;font-size:11px;color:#8ba3c4;">{label}</td>
          <td style="padding:3px 6px;">
            <div style="background:#ffffff0a;border-radius:3px;height:6px;overflow:hidden;">
              <div style="background:{color};height:6px;width:{pct}%;border-radius:3px;"></div>
            </div>
          </td>
          <td width="30px" align="right" style="padding:3px 0;font-family:monospace;font-size:10px;color:{color};font-weight:700;">{count}</td>
        </tr>""")
    return "\n".join(rows)
