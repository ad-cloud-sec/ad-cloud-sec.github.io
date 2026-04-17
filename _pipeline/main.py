#!/usr/bin/env python3
"""
CyberSec Intelligence Dashboard — main entry point.

Usage:
    python main.py                  # run pipeline and open browser
    python main.py --no-browser     # run without opening browser
"""

import os
import sys
import logging
import webbrowser
import argparse
from pathlib import Path
from datetime import datetime

# ── Bootstrap ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_FILE  = BASE_DIR / "dashboard.log"

# Load .env before anything else
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # dotenv not installed yet; that's fine, env vars may be set another way
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)
# Make the stream handler safe on Windows consoles that only support cp1252
logging.getLogger().handlers[0].stream = open(
    sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", closefd=False
)
logger = logging.getLogger("dashboard")


def main(open_browser: bool = True) -> None:
    logger.info("-" * 60)
    logger.info("  AD-SEC INTEL Dashboard  -  %s",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("-" * 60)

    # ── Dependency check ──────────────────────────────────────────────────────
    _check_dependencies()

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            "ANTHROPIC_API_KEY not set — dashboard will display raw headlines "
            "without AI summaries. Set the key in .env to enable AI features."
        )

    # ── 1. Fetch all data sources ─────────────────────────────────────────────
    logger.info("[1/3] Fetching feeds …")
    from fetchers import fetch_all_data
    raw_items, github_repos = fetch_all_data()
    logger.info("      %d raw items  |  %d GitHub repos", len(raw_items), len(github_repos))

    if not raw_items:
        logger.error("No items fetched — check your network connection and logs.")
        sys.exit(1)

    # ── 2. AI categorisation & summarisation ──────────────────────────────────
    logger.info("[2/3] AI categorisation & summarisation …")
    from ai_processor import process_all_items
    data = process_all_items(raw_items, github_repos, api_key or None)

    cat_counts = {k: len(v) for k, v in data["categories"].items()}
    logger.info("      items per category: %s", cat_counts)

    # ── 3. Generate HTML ──────────────────────────────────────────────────────
    logger.info("[3/3] Generating dashboard HTML …")
    from dashboard_generator import generate_dashboard

    # Dated file: dashboard_2026-03-23_1915.html
    ts_stamp  = datetime.now().strftime("%Y-%m-%d_%H%M")
    dated_path = BASE_DIR / "archive" / f"dashboard_{ts_stamp}.html"
    latest_path = BASE_DIR / "dashboard.html"

    dated_path.parent.mkdir(exist_ok=True)
    generate_dashboard(data, dated_path)

    # Keep dashboard.html as a copy of the latest for the browser shortcut
    import shutil
    shutil.copy2(dated_path, latest_path)

    logger.info("      Saved → %s", dated_path)
    logger.info("      Latest → %s", latest_path)

    # ── Open in browser ───────────────────────────────────────────────────────
    if open_browser:
        webbrowser.open(latest_path.as_uri())
        logger.info("      Opened in default browser ✓")

    # ── Send via Gmail ────────────────────────────────────────────────────────
    logger.info("[+] Sending dashboard via Gmail …")
    try:
        from gmail_sender import send_dashboard_email
        send_dashboard_email(latest_path, data)
    except Exception as exc:
        logger.warning("Gmail delivery failed: %s — dashboard was still saved.", exc)

    logger.info("-" * 60)
    logger.info("  Done.  Dashboard -> %s", latest_path)
    logger.info("-" * 60)


def _check_dependencies() -> None:
    """Check that required packages are installed; exit with helpful message if not."""
    checks = [
        ("requests",  "requests"),
        ("feedparser", "feedparser"),
        ("dotenv",    "python-dotenv"),
        ("anthropic", "anthropic"),
    ]
    missing = []
    for import_name, pip_name in checks:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        logger.error(
            "Missing packages: %s\n"
            "  Run:  pip install -r requirements.txt",
            ", ".join(missing),
        )
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CyberSec Intelligence Dashboard — fetch, summarise, generate."
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Generate dashboard without opening it in the browser."
    )
    args = parser.parse_args()

    try:
        main(open_browser=not args.no_browser)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)
