#!/usr/bin/env python3
"""
Feed fetchers: RSS/Atom, NVD CVE API, CISA KEV, GitHub search.

Every source is fetched independently. Failures are caught, logged, and
skipped — the pipeline always continues with whatever data it has.
"""

import os
import re
import time
import hashlib
import logging
import difflib
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
import feedparser

logger = logging.getLogger("dashboard.fetchers")

# ── Config ─────────────────────────────────────────────────────────────────────
TIMEOUT       = 20           # HTTP timeout (seconds)
LOOKBACK_DAYS = 7            # max age of items to keep
DEDUP_THRESH  = 0.72         # title-similarity threshold for dedup
USER_AGENT    = (
    "CyberSecDashboard/1.0 (local intelligence feed aggregator; "
    "contact via https://github.com/local/cybersec-dashboard)"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

# ── RSS / Atom feeds ───────────────────────────────────────────────────────────
RSS_FEEDS = [
    # ── General security news ──────────────────────────────────────────────────
    {"name": "The Hacker News",         "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "Bleeping Computer",       "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "Krebs on Security",       "url": "https://krebsonsecurity.com/feed/"},
    {"name": "Dark Reading",            "url": "https://www.darkreading.com/rss.xml"},
    {"name": "Schneier on Security",    "url": "https://www.schneier.com/blog/atom.xml"},
    {"name": "SANS ISC",                "url": "https://isc.sans.edu/rssfeed.xml"},
    {"name": "SecurityWeek",            "url": "https://feeds.feedburner.com/securityweek"},
    {"name": "Security Affairs",        "url": "https://securityaffairs.com/feed"},
    {"name": "Ars Technica Security",   "url": "https://arstechnica.com/security/feed/"},
    {"name": "Wired Security",          "url": "https://www.wired.com/feed/category/security/latest/rss"},
    {"name": "Infosecurity Magazine",   "url": "https://www.infosecurity-magazine.com/rss/news/"},
    {"name": "Rapid7 Blog",             "url": "https://blog.rapid7.com/rss/"},
    {"name": "NCC Group Research",      "url": "https://research.nccgroup.com/feed/"},
    {"name": "Google Project Zero",     "url": "https://googleprojectzero.blogspot.com/feeds/posts/default"},
    {"name": "TrendMicro Research",     "url": "https://feeds.trendmicro.com/Anti-Malware-Research"},
    {"name": "Malwarebytes Labs",       "url": "https://www.malwarebytes.com/blog/feed/"},
    {"name": "Sophos X-Ops",           "url": "https://news.sophos.com/en-us/feed/"},
    # ── Cloud security ─────────────────────────────────────────────────────────
    {"name": "AWS Security Blog",       "url": "https://aws.amazon.com/blogs/security/feed/"},
    {"name": "Google Security Blog",    "url": "https://security.googleblog.com/feeds/posts/default"},
    {"name": "Microsoft Security",      "url": "https://www.microsoft.com/en-us/security/blog/feed/"},
    {"name": "Cloudflare Blog",         "url": "https://blog.cloudflare.com/tag/security/rss"},
    {"name": "Sysdig Threat Research",  "url": "https://sysdig.com/blog/feed/"},
    {"name": "Wiz Blog",               "url": "https://www.wiz.io/blog/rss.xml"},
    # ── Threat intelligence ────────────────────────────────────────────────────
    {"name": "Palo Alto Unit42",        "url": "https://unit42.paloaltonetworks.com/feed/"},
    {"name": "Talos Intelligence",      "url": "https://blog.talosintelligence.com/rss/"},
    {"name": "Mandiant Blog",           "url": "https://www.mandiant.com/resources/blog/rss.xml"},
    {"name": "Recorded Future",         "url": "https://www.recordedfuture.com/feed"},
    {"name": "Sentinel One Blog",       "url": "https://www.sentinelone.com/blog/feed/"},
    {"name": "CrowdStrike Blog",        "url": "https://www.crowdstrike.com/blog/feed/"},
    {"name": "Securelist",             "url": "https://securelist.com/feed/"},
    {"name": "Check Point Research",    "url": "https://research.checkpoint.com/feed/"},
    {"name": "IBM Security Intel",      "url": "https://securityintelligence.com/feed/"},
    # ── Vulnerability research ─────────────────────────────────────────────────
    {"name": "Zero Day Initiative",     "url": "https://www.zerodayinitiative.com/rss/published/"},
    {"name": "Exploit-DB",              "url": "https://www.exploit-db.com/rss.xml"},
    {"name": "VulnHub",                 "url": "https://www.vulnhub.com/rss.xml"},
    {"name": "Tenable Research",        "url": "https://www.tenable.com/blog/feed"},
    # ── Detection & defense ────────────────────────────────────────────────────
    {"name": "The DFIR Report",        "url": "https://thedfirreport.com/feed/"},
    {"name": "Red Canary",             "url": "https://redcanary.com/blog/feed/"},
    {"name": "Huntress Blog",          "url": "https://www.huntress.com/blog/rss.xml"},
    {"name": "Elastic Security Labs",  "url": "https://www.elastic.co/security-labs/rss/feed.xml"},
    {"name": "LetsDefend Blog",        "url": "https://app.letsdefend.io/blog/rss"},
    {"name": "AttackIQ Blog",          "url": "https://www.attackiq.com/blog/feed/"},
    # ── AI & LLM security ─────────────────────────────────────────────────────
    {"name": "Embrace The Red",        "url": "https://embracethered.com/blog/index.xml"},
    {"name": "LLM Security",           "url": "https://llmsecurity.net/index.xml"},
    {"name": "Simon Willison (AI sec)","url": "https://simonwillison.net/atom/everything/"},
    # ── Government CERTs ──────────────────────────────────────────────────────
    {"name": "CISA Advisories",         "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml"},
    {"name": "CISA ICS Advisories",    "url": "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml"},
    {"name": "NCSC UK",                "url": "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml"},
    {"name": "CERT-EU",                "url": "https://cert.europa.eu/publications/security-advisories/feed"},
    {"name": "ASD ACSC Alerts",        "url": "https://www.cyber.gov.au/about-us/view-all-content/alerts-and-advisories/rss"},
    # ── Security product launches & industry news ──────────────────────────────
    {"name": "Help Net Security",       "url": "https://www.helpnetsecurity.com/feed/"},
    {"name": "SC Media",                "url": "https://www.scmagazine.com/feed/"},
    {"name": "VentureBeat Security",    "url": "https://venturebeat.com/security/feed/"},
    {"name": "TechCrunch Security",     "url": "https://techcrunch.com/category/security/feed/"},
    {"name": "Security Boulevard",      "url": "https://securityboulevard.com/feed/"},
    {"name": "The Register Security",   "url": "https://www.theregister.com/security/headlines.atom"},
    {"name": "CyberScoop",             "url": "https://cyberscoop.com/feed/"},
    {"name": "Risky Business",         "url": "https://risky.biz/feeds/risky-business/"},
]

NVD_API_URL   = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV_URL  = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
GITHUB_API    = "https://api.github.com/search/repositories"


# ══ Public entry point ═════════════════════════════════════════════════════════

def fetch_all_data() -> tuple:
    """
    Returns (news_items: list[dict], github_repos: list[dict]).
    Each news item is a normalised dict ready for AI processing.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    items: list = []

    # ── RSS feeds ──────────────────────────────────────────────────────────────
    for feed in RSS_FEEDS:
        try:
            batch = _fetch_rss(feed["name"], feed["url"], cutoff)
            items.extend(batch)
            logger.info("  ✓ %-26s %d items", feed["name"], len(batch))
        except Exception as exc:
            logger.warning("  ✗ %-26s FAILED: %s", feed["name"], exc)
        time.sleep(0.4)   # polite inter-request delay

    # ── NVD CVE API ────────────────────────────────────────────────────────────
    try:
        nvd = _fetch_nvd(cutoff)
        items.extend(nvd)
        logger.info("  ✓ %-26s %d items", "NVD CVE API", len(nvd))
    except Exception as exc:
        logger.warning("  ✗ %-26s FAILED: %s", "NVD CVE API", exc)

    # ── CISA KEV ───────────────────────────────────────────────────────────────
    try:
        kev = _fetch_cisa_kev(cutoff)
        items.extend(kev)
        logger.info("  ✓ %-26s %d items", "CISA KEV", len(kev))
    except Exception as exc:
        logger.warning("  ✗ %-26s FAILED: %s", "CISA KEV", exc)

    # Deduplicate before returning
    items = _deduplicate(items)
    logger.info("  → %d unique items after deduplication", len(items))

    # ── GitHub trending security repos ─────────────────────────────────────────
    repos: list = []
    try:
        repos = _fetch_github_security()
        logger.info("  ✓ %-26s %d repos", "GitHub Trending", len(repos))
    except Exception as exc:
        logger.warning("  ✗ %-26s FAILED: %s", "GitHub Trending", exc)

    return items, repos


# ══ Private helpers ════════════════════════════════════════════════════════════

def _parse_entry_date(entry) -> Optional[datetime]:
    """Extract a timezone-aware datetime from a feedparser entry."""
    import calendar

    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        tup = getattr(entry, attr, None)
        if tup:
            try:
                return datetime.fromtimestamp(calendar.timegm(tup), tz=timezone.utc)
            except Exception:
                pass

    from email.utils import parsedate_to_datetime
    for attr in ("published", "updated", "dc_date"):
        s = getattr(entry, attr, None)
        if s:
            try:
                return parsedate_to_datetime(s).astimezone(timezone.utc)
            except Exception:
                pass
    return None


def _strip_html(html: str, max_len: int = 600) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _normalise(
    *,
    title: str,
    url: str,
    description: str,
    source: str,
    pub_dt: Optional[datetime],
    severity_hint: str = "Interesting",
    category_hint: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Build a canonical item dict."""
    uid = hashlib.md5(url.encode()).hexdigest()
    pub_str = pub_dt.strftime("%Y-%m-%d %H:%M UTC") if pub_dt else "Unknown date"
    d = {
        "id":            uid,
        "title":         title.strip(),
        "description":   description.strip(),
        "url":           url.strip(),
        "source":        source,
        "published_dt":  pub_dt,
        "published_str": pub_str,
        "severity_hint": severity_hint,
        "category_hint": category_hint,
        # Filled by ai_processor:
        "summary":       None,
        "severity":      None,
        "category":      None,
        "include":       None,
    }
    if extra:
        d.update(extra)
    return d


# ── RSS/Atom ───────────────────────────────────────────────────────────────────

def _fetch_rss(source_name: str, url: str, cutoff: datetime) -> list:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    items = []
    for entry in feed.entries:
        pub_dt = _parse_entry_date(entry)
        if pub_dt and pub_dt < cutoff:
            continue

        title = getattr(entry, "title", "").strip()
        link  = getattr(entry, "link",  "").strip()
        if not title or not link:
            continue

        # Pick best description field
        raw_desc = ""
        for attr in ("summary", "description", "content"):
            val = getattr(entry, attr, None)
            if val:
                if isinstance(val, list):
                    val = val[0].get("value", "") if val else ""
                raw_desc = val
                break

        items.append(_normalise(
            title=title,
            url=link,
            description=_strip_html(raw_desc),
            source=source_name,
            pub_dt=pub_dt,
        ))

    return items


# ── NVD CVE API ───────────────────────────────────────────────────────────────

def _fetch_nvd(cutoff: datetime) -> list:
    api_key = os.getenv("NVD_API_KEY", "").strip()
    now     = datetime.now(timezone.utc)

    params = {
        "pubStartDate":   cutoff.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate":     now.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "resultsPerPage": 100,
    }
    h = dict(HEADERS)
    if api_key:
        h["apiKey"] = api_key

    resp = requests.get(NVD_API_URL, params=params, headers=h, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    items = []
    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")

        # English description
        descriptions = cve.get("descriptions", [])
        desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

        # CVSS score (prefer v3.1, fall back to v3.0, v2)
        cvss_score = None
        metrics = cve.get("metrics", {})
        for ver in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            m_list = metrics.get(ver, [])
            if m_list:
                cvss_score = m_list[0].get("cvssData", {}).get("baseScore")
                break

        pub_dt = None
        pub_str = cve.get("published", "")
        if pub_str:
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except Exception:
                pass

        severity_hint = (
            "Critical"    if cvss_score and cvss_score >= 9.0 else
            "High"        if cvss_score and cvss_score >= 7.0 else
            "Interesting"
        )

        short_desc = desc[:90].rstrip() + ("…" if len(desc) > 90 else "")
        title = f"{cve_id} — {short_desc}" if short_desc else cve_id

        items.append(_normalise(
            title=title,
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            description=desc[:600],
            source="NVD CVE API",
            pub_dt=pub_dt,
            severity_hint=severity_hint,
            category_hint="cve_vuln",
            extra={"cvss": cvss_score},
        ))

    # Respect rate limit: 5 req / 30 s without key
    if not api_key:
        time.sleep(6)

    return items


# ── CISA KEV ──────────────────────────────────────────────────────────────────

def _fetch_cisa_kev(cutoff: datetime) -> list:
    resp = requests.get(CISA_KEV_URL, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    items = []
    for vuln in data.get("vulnerabilities", []):
        date_str = vuln.get("dateAdded", "")
        try:
            pub_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if pub_dt < cutoff:
            continue

        cve_id = vuln.get("cveID", "")
        name   = vuln.get("vulnerabilityName", "")
        title  = f"[CISA KEV] {cve_id} — {name}"
        desc   = (
            f"{vuln.get('shortDescription', '')} "
            f"Required action: {vuln.get('requiredAction', '')} "
            f"(Due: {vuln.get('dueDate', 'N/A')})"
        ).strip()

        items.append(_normalise(
            title=title,
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            description=desc[:600],
            source="CISA KEV",
            pub_dt=pub_dt,
            severity_hint="Critical",   # KEV = actively exploited
            category_hint="cve_vuln",
        ))

    return items


# ── GitHub ────────────────────────────────────────────────────────────────────

def _fetch_github_security() -> list:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    h = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"

    since_7d  = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    queries = [
        # Newly created repos in last 7 days (catching brand-new tools)
        f"topic:security created:>{since_7d}",
        f"topic:cybersecurity created:>{since_7d}",
        f"topic:penetration-testing created:>{since_7d}",
        f"topic:red-team created:>{since_7d}",
        f"topic:exploit created:>{since_7d}",
        # Repos created up to 30 days ago that are gaining stars fast
        # (catches PentAGI-level tools that launched recently but aren't brand new)
        f"topic:security created:>{since_30d} stars:>50",
        f"topic:cybersecurity created:>{since_30d} stars:>50",
        f"topic:penetration-testing created:>{since_30d} stars:>30",
        f"topic:offensive-security created:>{since_30d} stars:>30",
        f"topic:red-team created:>{since_30d} stars:>30",
        # High-signal keyword searches for tools that may not have proper topics set
        f"security hacking tool created:>{since_30d} stars:>100",
        f"pentest framework created:>{since_30d} stars:>50",
        f"vulnerability scanner created:>{since_30d} stars:>50",
        f"malware analysis created:>{since_30d} stars:>50",
    ]

    seen: set = set()
    repos: list = []

    for q in queries:
        try:
            resp = requests.get(
                GITHUB_API,
                headers=h,
                params={"q": q, "sort": "stars", "order": "desc", "per_page": 10},
                timeout=TIMEOUT,
            )
            if resp.status_code == 422:
                logger.debug("GitHub query '%s' returned 422 (no results), skipping.", q)
                continue
            resp.raise_for_status()
            for repo in resp.json().get("items", []):
                rid = repo["id"]
                if rid in seen:
                    continue
                seen.add(rid)
                repos.append({
                    "id":          str(rid),
                    "name":        repo["full_name"],
                    "description": repo.get("description") or "",
                    "url":         repo["html_url"],
                    "stars":       repo.get("stargazers_count", 0),
                    "language":    repo.get("language") or "Unknown",
                    "topics":      repo.get("topics", []),
                    "created_at":  repo.get("created_at", ""),
                    "source":      "GitHub Trending",
                })
        except Exception as exc:
            logger.warning("  GitHub query '%s' failed: %s", q, exc)
        time.sleep(1.2)   # GitHub search: 10 req/min unauthenticated

    # Highest-star repos first, cap at 30
    repos.sort(key=lambda r: r["stars"], reverse=True)
    return repos[:30]


# ── Deduplication ─────────────────────────────────────────────────────────────

def _deduplicate(items: list, threshold: float = DEDUP_THRESH) -> list:
    """
    Remove near-duplicate items.
    Uses URL exact-match first, then title similarity via SequenceMatcher.
    O(n²) — acceptable for typical feed volumes (a few hundred items).
    """
    unique: list = []
    seen_urls: set = set()
    seen_titles: list = []

    for item in items:
        url   = item.get("url", "")
        title = item.get("title", "").lower()

        if url and url in seen_urls:
            continue

        if any(
            difflib.SequenceMatcher(None, title, t).ratio() > threshold
            for t in seen_titles
        ):
            continue

        if url:
            seen_urls.add(url)
        seen_titles.append(title)
        unique.append(item)

    return unique
