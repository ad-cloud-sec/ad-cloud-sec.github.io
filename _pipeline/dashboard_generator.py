#!/usr/bin/env python3
"""
Generates a single self-contained HTML dashboard file.
All CSS and JS are embedded inline — no CDN dependencies, fully offline-readable.
"""

import base64
import html
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.generator")

# ── Font embedding ─────────────────────────────────────────────────────────────
_FONT_DIR = Path(__file__).parent

def _load_font_b64(filename: str) -> str:
    """Return base64-encoded font or empty string if file not found."""
    p = _FONT_DIR / filename
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()

def _build_font_face() -> str:
    """Build @font-face block for JetBrains Mono if available."""
    b64 = _load_font_b64("JetBrainsMono-VariableFont_wght.ttf")
    if not b64:
        return ""
    return f"""@font-face {{
  font-family: 'JetBrains Mono';
  src: url('data:font/truetype;base64,{b64}') format('truetype');
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}}
"""

def _minify_css(css: str) -> str:
    """Basic CSS minifier — strips comments and collapses whitespace."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    css = re.sub(r'\s*([{};:,>~+])\s*', r'\1', css)
    css = re.sub(r'\s+', ' ', css)
    return css.strip()

def _favicon_svg() -> str:
    """Inline SVG favicon — shield with brand green."""
    import urllib.parse
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2300c896" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>'
    return svg

# ── Brand ──────────────────────────────────────────────────────────────────────
BRAND   = "AD-SEC INTEL"
TAGLINE = "Cybersecurity Intelligence"

# ── Inline SVG icons (Feather / Lucide style, 24 × 24) ────────────────────────
_I = {
    "logo":    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
    "cve":     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "cloud":   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/></svg>',
    "cpu":     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
    "target":  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "shield":  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "box":     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "star":    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "book":    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    "search":  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "chevron": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
    "link":    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
    "rss":     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1" fill="currentColor"/></svg>',
    "x":       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
}

# ── Category metadata ──────────────────────────────────────────────────────────
CAT_META = {
    "cve_vuln": {
        "label":    "CVEs & Vulnerabilities",
        "sublabel": "Exploits · Patches · Advisories",
        "icon":     "cve",
        "color":    "#f43f5e",
        "id":       "cve-vuln",
    },
    "cloud_security": {
        "label":    "Cloud Security",
        "sublabel": "AWS · Azure · GCP · Kubernetes",
        "icon":     "cloud",
        "color":    "#0ea5e9",
        "id":       "cloud-security",
    },
    "ai_llm_security": {
        "label":    "AI / LLM Security",
        "sublabel": "Prompt injection · Model attacks · AI red team",
        "icon":     "cpu",
        "color":    "#a855f7",
        "id":       "ai-llm",
    },
    "threat_intel": {
        "label":    "Threat Intelligence",
        "sublabel": "APTs · Ransomware · Campaigns · IOCs",
        "icon":     "target",
        "color":    "#f97316",
        "id":       "threat-intel",
    },
    "offensive_defensive": {
        "label":    "Offensive & Defensive",
        "sublabel": "Red team · Blue team · Tools · Detections",
        "icon":     "shield",
        "color":    "#10b981",
        "id":       "offensive-defensive",
    },
    "product_launches": {
        "label":    "Product Launches",
        "sublabel": "New tools · Funding · GA releases",
        "icon":     "box",
        "color":    "#eab308",
        "id":       "product-launches",
    },
    "new_notable": {
        "label":    "New & Notable",
        "sublabel": "Open source · Research · Trending repos",
        "icon":     "star",
        "color":    "#ec4899",
        "id":       "new-notable",
    },
}

DIGEST_LABELS = {
    "cve_vuln":            ("cve",    "#f43f5e", "CVEs & Vulns"),
    "cloud_security":      ("cloud",  "#0ea5e9", "Cloud Security"),
    "ai_llm_security":     ("cpu",    "#a855f7", "AI / LLM Security"),
    "threat_intel":        ("target", "#f97316", "Threat Intel"),
    "offensive_defensive": ("shield", "#10b981", "Offense & Defense"),
}

_CVE_RE = re.compile(r'(CVE-\d{4}-\d+)', re.IGNORECASE)

CAT_ORDER = (
    "cve_vuln", "cloud_security", "ai_llm_security",
    "threat_intel", "offensive_defensive", "product_launches", "new_notable",
)


# ══ Public entry point ═════════════════════════════════════════════════════════

def generate_dashboard(data: dict, output_path: Path) -> None:
    """Write the complete HTML dashboard to output_path."""
    doc = _build_html(data)
    output_path.write_text(doc, encoding="utf-8")
    logger.info("  HTML size: %.1f KB", len(doc) / 1024)


# ══ HTML building ══════════════════════════════════════════════════════════════

def _build_html(data: dict) -> str:
    generated_at = data.get("generated_at", datetime.now(timezone.utc).isoformat())
    try:
        dt         = datetime.fromisoformat(generated_at)
        ts_display = dt.strftime("%d %b %Y · %H:%M UTC")
        ts_date    = dt.strftime("%d %b %Y")
    except Exception:
        ts_display = ts_date = generated_at

    categories     = data.get("categories", {})
    weekly         = data.get("weekly_digest", {})
    total_shown    = data.get("total_shown", 0)
    total_raw      = data.get("total_raw", 0)
    today_count    = data.get("today_count", 0)
    yesterday_count= data.get("yesterday_count", 0)

    critical_n = sum(1 for items in categories.values() for i in items if i.get("severity") == "Critical")
    high_n     = sum(1 for items in categories.values() for i in items if i.get("severity") == "High")

    # Trend delta
    if yesterday_count > 0:
        delta     = today_count - yesterday_count
        delta_sign= "+" if delta > 0 else ""
        delta_cls = "tb-delta-up" if delta > 0 else ("tb-delta-down" if delta < 0 else "tb-delta-flat")
        delta_html= f'<span class="tb-delta {delta_cls}">{delta_sign}{delta} vs yday</span>'
    else:
        delta_html = ""

    # Sections
    sidebar_html     = _render_sidebar(categories)
    sections_html    = "".join(_render_section(CAT_META[k], categories.get(k, []), k) for k in CAT_ORDER)
    digest_html      = _render_digest(weekly)
    top_stories_html = _render_top_stories(_pick_top_stories(categories))

    # THREATCON bar (replaces breaking banner)
    tc_level, tc_color, tc_bg, tc_desc, tc_rank = _threatcon_level(critical_n, high_n)
    threatcon_html = _render_threatcon_bar(tc_level, tc_color, tc_bg, tc_desc, tc_rank)
    breaking_html  = threatcon_html  # keep var name for template below

    font_face  = _build_font_face()
    minified   = _minify_css(font_face + _CSS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{BRAND} — {TAGLINE}</title>
<meta name="description" content="Daily cybersecurity intelligence: CVEs, threat intel, cloud security, AI/LLM threats — curated by AD-SEC INTEL.">
<meta property="og:title" content="{BRAND}">
<meta property="og:description" content="Daily cybersecurity intelligence dashboard — {ts_date}">
<meta property="og:type" content="website">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,{_favicon_svg()}">
<style>
{minified}
</style>
</head>
<body>
<!-- Background layers (grid + orbs) -->
<div class="bg-orbs" aria-hidden="true">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
</div>
<div class="bg-grid" aria-hidden="true"></div>

<!-- ══ Topbar ═══════════════════════════════════════════════════════════════ -->
<div class="topbar">
  <span class="topbar-brand">{_I['logo']} {BRAND}</span>
  <span class="topbar-updated">Updated {ts_display}</span>
  <div class="topbar-stats">
    <span class="tb-stat tb-critical">{critical_n} Critical</span>
    <span class="tb-stat tb-high">{high_n} High</span>
    <span class="tb-stat tb-total">{total_shown} Stories {delta_html}</span>
  </div>
</div>

<!-- ══ Header ════════════════════════════════════════════════════════════════ -->
<header class="site-header">
  <div class="header-inner">

    <a href="#" class="brand-link" aria-label="{BRAND} home">
      <div class="brand-icon">{_I['logo']}</div>
      <div class="brand-text">
        <span class="brand-name">{BRAND}</span>
        <span class="brand-tagline">{TAGLINE}</span>
      </div>
    </a>

    <div class="header-search">
      <div class="search-wrap">
        <span class="search-icon-wrap">{_I['search']}</span>
        <input type="text" id="search" placeholder="Search stories…" autocomplete="off" spellcheck="false" aria-label="Search stories">
        <button id="clear-search" title="Clear" aria-label="Clear search">{_I['x']}</button>
      </div>
      <span class="search-hint">Press <kbd>/</kbd> to focus · <kbd>Esc</kbd> to clear</span>
    </div>

    <nav class="header-nav" aria-label="Quick navigation">
      <a href="#weekly-digest"    class="hn-link hn-brand">{_I['book']} Weekly Brief</a>
      <a href="#cve-vuln"         class="hn-link" style="--c:#f43f5e">{_I['cve']} CVEs</a>
      <a href="#threat-intel"     class="hn-link" style="--c:#f97316">{_I['target']} Intel</a>
      <a href="#ai-llm"           class="hn-link" style="--c:#a855f7">{_I['cpu']} AI/LLM</a>
    </nav>

  </div>
</header>
{breaking_html}

<!-- ══ Page layout ═══════════════════════════════════════════════════════════ -->
<div class="page-layout">

  <!-- Sidebar -->
  <aside class="sidebar" aria-label="Category navigation">
    <div class="sidebar-inner">
{sidebar_html}
      <div class="sidebar-footer">
        <div class="sf-row">{_I['rss']} {total_raw} items fetched</div>
        <div class="sf-row">{_I['star']} {ts_date}</div>
      </div>
    </div>
  </aside>

  <!-- Main -->
  <main class="main-content">

{top_stories_html}

    <section id="weekly-digest" class="digest-section">
      <div class="section-header" data-target="digest-body">
        <div class="sh-left">
          <div class="sh-icon-wrap sh-icon-brand">{_I['book']}</div>
          <div class="sh-titles">
            <span class="sh-eyebrow">7-day round-up · AI curated</span>
            <h2 class="sh-heading">Weekly Brief</h2>
          </div>
        </div>
        <button class="collapse-btn" aria-label="Toggle section">{_I['chevron']}</button>
      </div>
      <div id="digest-body" class="digest-grid">
{digest_html}
      </div>
    </section>

{sections_html}

  </main>
</div>

<!-- ══ Footer ════════════════════════════════════════════════════════════════ -->
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <span class="footer-logo">{_I['logo']}</span>
      <span class="footer-name">{BRAND}</span>
    </div>
    <p class="footer-copy">
      Aggregated from {total_raw} raw items · NVD CVE API · CISA KEV · 30+ RSS feeds · GitHub Trending.
      For security research and awareness only.
    </p>
  </div>
</footer>

<script>
{_JS}
</script>
</body>
</html>"""


# ── Sidebar ────────────────────────────────────────────────────────────────────

def _render_sidebar(categories: dict) -> str:
    lines = []
    lines.append(f"""      <a href="#top-stories" class="sb-link sb-top">
        <span class="sb-icon">{_I['star']}</span>
        <span class="sb-label">Lead Stories</span>
        <span class="sb-badge sb-badge-live">LIVE</span>
      </a>""")
    lines.append(f"""      <a href="#weekly-digest" class="sb-link sb-digest">
        <span class="sb-icon">{_I['book']}</span>
        <span class="sb-label">Weekly Brief</span>
        <span class="sb-badge sb-badge-brand">7d</span>
      </a>""")

    for cat_key in CAT_ORDER:
        meta  = CAT_META[cat_key]
        count = len(categories.get(cat_key, []))
        icon  = _I.get(meta["icon"], "")
        zero  = " sb-badge-zero" if count == 0 else ""
        lines.append(f"""      <a href="#{meta['id']}" class="sb-link" style="--cat:{meta['color']}">
        <span class="sb-icon">{icon}</span>
        <span class="sb-label">{html.escape(meta['label'])}</span>
        <span class="sb-badge{zero}">{count}</span>
      </a>""")

    return "\n".join(lines)


# ── Section ────────────────────────────────────────────────────────────────────

def _render_section(meta: dict, items: list, cat_key: str) -> str:
    color   = meta["color"]
    label   = meta["label"]
    sublabel = meta["sublabel"]
    icon    = _I.get(meta["icon"], "")
    sec_id  = meta["id"]
    body_id = f"body-{sec_id}"
    count   = len(items)

    if items:
        cards_html = "\n".join(_render_item_card(item) for item in items)
    else:
        cards_html = '<p class="no-items">No items in the last 24 hours.</p>'

    zero_cls = " sh-count-zero" if count == 0 else ""

    return f"""
    <section id="{sec_id}" class="cat-section" style="--cat:{color}">
      <div class="section-header" data-target="{body_id}">
        <div class="sh-left">
          <div class="sh-icon-wrap">{icon}</div>
          <div class="sh-titles">
            <h2 class="sh-heading">{html.escape(label)}</h2>
            <span class="sh-sub">{html.escape(sublabel)}</span>
          </div>
        </div>
        <div class="sh-right">
          <span class="sh-count{zero_cls}">{count}</span>
          <button class="collapse-btn" aria-label="Toggle section">{_I['chevron']}</button>
        </div>
      </div>
      <div id="{body_id}" class="section-body items-grid">
{cards_html}
      </div>
    </section>"""


# ── Item card ──────────────────────────────────────────────────────────────────

def _render_item_card(item: dict) -> str:
    title_esc    = html.escape(item.get("title", "Untitled"))
    title_html   = _CVE_RE.sub(r'<code class="cve-id">\1</code>', title_esc)
    summary      = html.escape(item.get("summary") or item.get("description") or "")
    source       = html.escape(item.get("source", "Unknown"))
    url          = html.escape(item.get("url", "#"))
    pub_str      = html.escape(item.get("published_str", ""))
    sev          = item.get("severity", "Interesting")
    time_ago     = _fmt_time_ago(item.get("published_dt"))

    sev_class = {"Critical": "sev-critical", "High": "sev-high"}.get(sev, "sev-info")
    sev_label = {"Critical": "Critical", "High": "High", "Interesting": "Info"}.get(sev, "Info")
    sev_pill  = f"sev-pill-{sev.lower()}"

    cvss      = item.get("cvss")
    cvss_html = f'<span class="cvss-badge">CVSS&nbsp;{cvss:.1f}</span>' if cvss else ""

    epss = item.get("epss")
    if epss and epss >= 0.7:
        epss_html = f'<span class="epss-badge epss-high">EPSS&nbsp;{epss:.0%}</span>'
    elif epss and epss >= 0.3:
        epss_html = f'<span class="epss-badge epss-med">EPSS&nbsp;{epss:.0%}</span>'
    else:
        epss_html = ""

    kev_html     = '<span class="kev-badge">KEV ⚑</span>'        if item.get("kev")         else ""
    exploit_html = '<span class="exploit-badge">PoC Public</span>' if item.get("has_exploit") and not item.get("kev") else ""

    source_count = item.get("source_count", 1)
    if source_count >= 5:
        trending_html = f'<span class="trending-badge hot">{source_count} sources</span>'
    elif source_count >= 3:
        trending_html = f'<span class="trending-badge">{source_count} sources</span>'
    else:
        trending_html = ""

    pub_dt = item.get("published_dt")
    is_breaking = pub_dt and (datetime.now(timezone.utc) - (pub_dt if pub_dt.tzinfo else pub_dt.replace(tzinfo=timezone.utc))).total_seconds() < 7200
    breaking_tag = '<span class="breaking-tag">BREAKING</span>' if is_breaking else ""

    return f"""        <article class="item-card {sev_class} searchable">
          <div class="card-top">
            <span class="card-source">{source}</span>
            {breaking_tag}
            {trending_html}
            <span class="card-time">{time_ago}</span>
          </div>
          <h3 class="card-title">
            <a href="{url}" target="_blank" rel="noopener noreferrer">{title_html}</a>
          </h3>
          <p class="card-summary">{summary}</p>
          <div class="card-footer">
            <span class="sev-pill {sev_pill}">{sev_label}</span>
            {cvss_html}
            {epss_html}
            {kev_html}
            {exploit_html}
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="read-link">Read {_I['link']}</a>
          </div>
        </article>"""


# ── Weekly digest ──────────────────────────────────────────────────────────────

def _render_digest(weekly: dict) -> str:
    cards = []
    for cat_key, (icon_key, color, label) in DIGEST_LABELS.items():
        entry = weekly.get(cat_key) if weekly else None
        icon  = _I.get(icon_key, "")

        if entry:
            title      = html.escape(entry.get("title",   ""))
            summary    = html.escape(entry.get("summary") or "")
            source     = html.escape(entry.get("source",  ""))
            url        = html.escape(entry.get("url",     "#"))
            title_html = _CVE_RE.sub(r'<code class="cve-id">\1</code>', title)
            cards.append(f"""        <article class="digest-card searchable" style="--dc:{color}">
          <div class="dc-cat">
            <span class="dc-icon">{icon}</span>
            <span class="dc-label">{label}</span>
          </div>
          <h3 class="dc-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title_html}</a></h3>
          <p class="dc-summary">{summary}</p>
          <div class="dc-footer">
            <span class="dc-source">via {source}</span>
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="read-link">Read {_I['link']}</a>
          </div>
        </article>""")
        else:
            cards.append(f"""        <article class="digest-card digest-card-empty" style="--dc:{color}">
          <div class="dc-cat">
            <span class="dc-icon">{icon}</span>
            <span class="dc-label">{label}</span>
          </div>
          <p class="dc-empty">No significant stories this week.</p>
        </article>""")

    return "\n".join(cards)


# ── Time formatting ────────────────────────────────────────────────────────────

def _fmt_time_ago(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    diff      = datetime.now(timezone.utc) - dt
    total_sec = diff.total_seconds()
    if total_sec < 3600:
        m = max(1, int(total_sec / 60))
        return f"{m}m ago"
    elif total_sec < 86400:
        return f"{int(total_sec / 3600)}h ago"
    elif total_sec < 604800:
        return f"{int(total_sec / 86400)}d ago"
    return f"{int(total_sec / 604800)}w ago"


# ── THREATCON ──────────────────────────────────────────────────────────────────

def _threatcon_level(critical_n: int, high_n: int):
    if critical_n > 0:
        return ("CRITICAL", "#f43f5e", "rgba(244,63,94,0.07)",
                f"{critical_n} critical {'advisory' if critical_n == 1 else 'advisories'} — immediate review recommended", 3)
    elif high_n >= 3:
        return ("HIGH", "#f97316", "rgba(249,115,22,0.05)",
                f"{high_n} high-severity threats identified today", 2)
    elif high_n > 0:
        return ("ELEVATED", "#eab308", "rgba(234,179,8,0.05)",
                "Elevated threat activity — monitor high-severity items", 1)
    else:
        return ("NORMAL", "#00c896", "rgba(0,200,150,0.04)",
                "Standard threat environment — no critical or high advisories", 0)


def _render_threatcon_bar(level: str, color: str, bg: str, desc: str, rank: int) -> str:
    pips = []
    labels = [("N", "NORMAL", 0), ("E", "ELEVATED", 1), ("H", "HIGH", 2), ("C", "CRITICAL", 3)]
    for ltr, _, r in labels:
        if r < rank:
            pips.append(f'<span class="tc-pip tc-pip-fill" style="background:{color};opacity:.45">{ltr}</span>')
        elif r == rank:
            pips.append(f'<span class="tc-pip tc-pip-active" style="background:{color};box-shadow:0 0 8px {color}">{ltr}</span>')
        else:
            pips.append(f'<span class="tc-pip">{ltr}</span>')
    pip_html = "".join(pips)
    pulse = ' tc-dot-pulse' if level == "CRITICAL" else ''
    return f"""
<div class="threatcon-bar" style="background:{bg};border-color:color-mix(in srgb,{color} 28%,transparent)" role="status">
  <span class="tc-dot{pulse}" style="background:{color};box-shadow:0 0 8px {color}"></span>
  <span class="tc-badge" style="color:{color};background:color-mix(in srgb,{color} 14%,transparent);border-color:color-mix(in srgb,{color} 30%,transparent)">THREATCON</span>
  <span class="tc-level-name" style="color:{color}">{level}</span>
  <span class="tc-divider">—</span>
  <span class="tc-desc">{html.escape(desc)}</span>
  <div class="tc-scale">{pip_html}</div>
</div>"""


# ── Top Stories ────────────────────────────────────────────────────────────────

_SEV_RANK = {"Critical": 0, "High": 1, "Interesting": 2}


def _pick_top_stories(categories: dict) -> list:
    priority = ["cve_vuln", "threat_intel", "ai_llm_security", "offensive_defensive", "cloud_security"]
    seen, stories = set(), []
    for cat in priority:
        items = categories.get(cat, [])
        if not items:
            continue
        def _key(i):
            s  = _SEV_RANK.get(i.get("severity", "Interesting"), 2)
            dt = i.get("published_dt")
            return (s, -(dt.timestamp() if dt else 0))
        for item in sorted(items, key=_key):
            url = item.get("url")
            if url and url not in seen:
                seen.add(url)
                stories.append((cat, item))
                break
        if len(stories) >= 3:
            break
    return stories


def _render_top_stories(stories: list) -> str:
    if not stories:
        return ""
    cards = []
    for cat_key, item in stories:
        meta       = CAT_META.get(cat_key, {})
        color      = meta.get("color", "#00c896")
        cat_label  = meta.get("label", cat_key)
        icon       = _I.get(meta.get("icon", "star"), "")
        title_esc  = html.escape(item.get("title", "Untitled"))
        title_html = _CVE_RE.sub(r'<code class="cve-id">\1</code>', title_esc)
        summary    = html.escape(item.get("summary") or item.get("description") or "")
        source     = html.escape(item.get("source", ""))
        url        = html.escape(item.get("url", "#"))
        time_ago   = _fmt_time_ago(item.get("published_dt"))
        sev        = item.get("severity", "Interesting")
        cvss       = item.get("cvss")
        cvss_html  = f'<span class="cvss-badge">CVSS&nbsp;{cvss:.1f}</span>' if cvss else ""
        sev_map    = {"Critical": ("sev-pill-critical", "Critical"), "High": ("sev-pill-high", "High")}
        sev_cls, sev_lbl = sev_map.get(sev, ("sev-pill-interesting", "Info"))
        cards.append(f"""        <article class="hero-card searchable" style="--hc:{color}">
          <div class="hc-meta">
            <span class="hc-cat-icon">{icon}</span>
            <span class="hc-cat-label" style="color:{color}">{html.escape(cat_label)}</span>
            <span class="hc-time">{time_ago}</span>
          </div>
          <h3 class="hc-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title_html}</a></h3>
          <p class="hc-summary">{summary}</p>
          <div class="hc-footer">
            <span class="sev-pill {sev_cls}">{sev_lbl}</span>
            {cvss_html}
            <span class="hc-source">via {source}</span>
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="read-link">Read {_I['link']}</a>
          </div>
        </article>""")
    cards_html = "\n".join(cards)
    return f"""
    <section id="top-stories" class="top-stories-section">
      <div class="ts-header">
        <span class="ts-eyebrow">● LIVE</span>
        <h2 class="ts-heading">Today's Lead Stories</h2>
        <span class="ts-sub">Highest-priority items across all categories</span>
      </div>
      <div class="hero-grid">
{cards_html}
      </div>
    </section>"""


# ══ CSS ════════════════════════════════════════════════════════════════════════
_CSS = """
/* ── Tokens ─────────────────────────────────────────────────────────────── */
:root {
  --glass-0:      rgba(255,255,255,0.022);
  --glass-1:      rgba(255,255,255,0.038);
  --glass-2:      rgba(255,255,255,0.058);
  --glass-3:      rgba(255,255,255,0.085);
  --glass-border: rgba(255,255,255,0.07);
  --glass-bright: rgba(255,255,255,0.13);
  --glass-inset:  inset 0 1px 0 rgba(255,255,255,0.07), inset 0 -1px 0 rgba(0,0,0,0.18);

  --text-1:    #eef4ff;
  --text-2:    #8ba3c4;
  --text-3:    #45607e;

  --brand:        #00c896;
  --brand-dim:    rgba(0,200,150,0.08);
  --brand-border: rgba(0,200,150,0.22);
  --brand-glow:   rgba(0,200,150,0.18);

  --critical:     #f43f5e;
  --critical-dim: rgba(244,63,94,0.08);
  --critical-glow:rgba(244,63,94,0.22);
  --high:         #f97316;
  --high-dim:     rgba(249,115,22,0.06);
  --high-glow:    rgba(249,115,22,0.18);

  --shadow-sm: 0 2px 8px rgba(0,0,0,0.35), 0 1px 2px rgba(0,0,0,0.25);
  --shadow-md: 0 8px 28px rgba(0,0,0,0.5),  0 2px 8px rgba(0,0,0,0.35);
  --shadow-lg: 0 24px 64px rgba(0,0,0,0.65),0 8px 24px rgba(0,0,0,0.45);

  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  --mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;

  --r-sm: 4px;
  --r-md: 8px;
  --r-lg: 14px;
  --r-xl: 18px;

  --topbar-h:  34px;
  --header-h:  64px;
  --sidebar-w: 232px;
}

/* ── Reset ───────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: #05060f;
  color: var(--text-1); font-family: var(--font); font-size: 14px; line-height: 1.6; min-height: 100vh;
  overflow-x: hidden;
}
a { color: var(--brand); text-decoration: none; }
a:hover { opacity: .8; }
svg { display: inline-block; vertical-align: middle; flex-shrink: 0; }

/* ── Background ambient lights (static — no animation avoids repaint issues) */
.bg-orbs {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
}
.orb { position: absolute; border-radius: 50%; filter: blur(100px); }
.orb-1 {
  width: 60vw; height: 60vw; top: -25%; left: -20%;
  background: radial-gradient(circle, rgba(37,99,235,0.13) 0%, transparent 65%);
}
.orb-2 {
  width: 50vw; height: 50vw; top: 25%; right: -20%;
  background: radial-gradient(circle, rgba(124,58,237,0.10) 0%, transparent 65%);
}
.orb-3 {
  width: 40vw; height: 40vw; bottom: -15%; left: 30%;
  background: radial-gradient(circle, rgba(0,200,150,0.08) 0%, transparent 65%);
}

.bg-grid {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse 100% 100% at 50% 0%, black 40%, transparent 100%);
}

/* All content above background layers */
.topbar, .site-header, .breaking-banner, .page-layout, .site-footer {
  position: relative; z-index: 1;
}

/* ── Topbar ──────────────────────────────────────────────────────────────── */
.topbar {
  height: var(--topbar-h);
  background: rgba(3,4,12,0.92);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid rgba(255,255,255,0.05);
  display: flex; align-items: center; gap: 16px; padding: 0 22px;
  position: sticky; top: 0; z-index: 300;
}
.topbar-brand {
  display: flex; align-items: center; gap: 6px;
  font-family: var(--mono); font-size: 11px; font-weight: 700; letter-spacing: .1em;
  color: var(--brand);
}
.topbar-brand svg { width: 13px; height: 13px; }
.topbar-updated { font-size: 11px; color: var(--text-3); font-family: var(--mono); }
.topbar-stats { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.tb-stat {
  font-size: 11px; font-weight: 600; font-family: var(--mono);
  padding: 2px 10px; border-radius: var(--r-sm); border: 1px solid;
  backdrop-filter: blur(8px);
}
.tb-critical { color: #fb7185; background: rgba(244,63,94,.12); border-color: rgba(244,63,94,.28); }
.tb-high     { color: #fb923c; background: rgba(249,115,22,.12); border-color: rgba(249,115,22,.28); }
.tb-total    { color: var(--text-2); background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.08); }

/* ── Header ──────────────────────────────────────────────────────────────── */
.site-header {
  height: var(--header-h);
  background: rgba(6,7,18,0.78);
  backdrop-filter: blur(32px) saturate(200%);
  -webkit-backdrop-filter: blur(32px) saturate(200%);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  box-shadow: 0 4px 32px rgba(0,0,0,0.5), var(--glass-inset);
  position: sticky; top: var(--topbar-h); z-index: 200;
}
.header-inner { height: 100%; display: flex; align-items: center; gap: 20px; padding: 0 22px; }

/* Brand */
.brand-link { display: flex; align-items: center; gap: 12px; text-decoration: none; flex-shrink: 0; }
.brand-link:hover { opacity: 1; }
.brand-icon {
  width: 40px; height: 40px;
  background: var(--brand-dim);
  border: 1px solid var(--brand-border);
  border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center; color: var(--brand);
  box-shadow: 0 0 20px var(--brand-glow), var(--shadow-sm);
  transition: box-shadow .3s;
}
.brand-icon:hover { box-shadow: 0 0 32px var(--brand-glow), var(--shadow-md); }
.brand-icon svg { width: 20px; height: 20px; }
.brand-text { display: flex; flex-direction: column; line-height: 1.2; }
.brand-name {
  font-family: var(--mono); font-size: 17px; font-weight: 800; letter-spacing: .1em;
  background: linear-gradient(135deg, #a5f3e8 0%, #00c896 40%, #6ee7b7 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.brand-tagline { font-size: 10px; color: var(--text-3); letter-spacing: .05em; text-transform: uppercase; margin-top: 1px; }

/* Search */
.header-search { flex: 1; max-width: 380px; display: flex; flex-direction: column; gap: 3px; }
.search-wrap {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: var(--r-md); padding: 0 12px; height: 36px;
  transition: border-color .2s, box-shadow .2s;
  backdrop-filter: blur(8px);
}
.search-wrap:focus-within {
  border-color: var(--brand-border);
  box-shadow: 0 0 0 3px var(--brand-dim), 0 0 16px rgba(0,200,150,0.1);
}
.search-icon-wrap { color: var(--text-3); display: flex; }
.search-icon-wrap svg { width: 14px; height: 14px; }
#search { flex: 1; background: transparent; border: none; outline: none; color: var(--text-1); font-size: 13px; font-family: var(--font); }
#search::placeholder { color: var(--text-3); }
#clear-search {
  background: transparent; border: none; color: var(--text-3);
  cursor: pointer; display: flex; align-items: center; padding: 3px; border-radius: var(--r-sm); transition: color .15s;
}
#clear-search:hover { color: var(--text-1); }
#clear-search svg { width: 13px; height: 13px; }
.search-hint { font-size: 10px; color: var(--text-3); padding-left: 2px; }
kbd {
  font-family: var(--mono); font-size: 9px;
  background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 3px; padding: 1px 4px; color: var(--text-2);
}

/* Header nav */
.header-nav { margin-left: auto; display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.hn-link {
  display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500;
  padding: 6px 11px; border-radius: var(--r-md); border: 1px solid transparent;
  color: var(--text-2); transition: all .2s;
}
.hn-link svg { width: 13px; height: 13px; }
.hn-link:hover {
  color: color-mix(in srgb, var(--c, var(--brand)) 100%, white);
  background: color-mix(in srgb, var(--c, var(--brand)) 10%, transparent);
  border-color: color-mix(in srgb, var(--c, var(--brand)) 30%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--c, var(--brand)) 20%, transparent);
  opacity: 1;
}
.hn-brand { color: var(--brand); }
.hn-brand:hover { background: var(--brand-dim); border-color: var(--brand-border); box-shadow: 0 0 16px var(--brand-glow); }

/* ── Breaking banner ─────────────────────────────────────────────────────── */
.breaking-banner {
  background: rgba(244,63,94,0.06);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(244,63,94,0.16);
  box-shadow: 0 4px 24px rgba(244,63,94,0.12);
  padding: 8px 22px; display: flex; align-items: center; gap: 10px; font-size: 12px;
}
.breaking-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--critical); flex-shrink: 0;
  box-shadow: 0 0 8px var(--critical);
  animation: blink 1.6s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1; box-shadow:0 0 8px var(--critical);} 50%{opacity:.25; box-shadow:none;} }
.breaking-label {
  font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .09em;
  color: var(--critical); background: rgba(244,63,94,.14); border: 1px solid rgba(244,63,94,.3);
  border-radius: var(--r-sm); padding: 1px 7px;
}
.breaking-text { color: var(--text-2); }
.breaking-text a { color: var(--critical); font-weight: 600; }

/* ── Page layout ─────────────────────────────────────────────────────────── */
.page-layout { display: flex; min-height: calc(100vh - var(--topbar-h) - var(--header-h)); }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-w); flex-shrink: 0;
  background: rgba(255,255,255,0.018);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255,255,255,0.055);
}
.sidebar-inner {
  position: sticky; top: calc(var(--topbar-h) + var(--header-h));
  max-height: calc(100vh - var(--topbar-h) - var(--header-h));
  overflow-y: auto; padding: 14px 0; display: flex; flex-direction: column; gap: 2px;
}
.sidebar-inner::-webkit-scrollbar { width: 3px; }
.sidebar-inner::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

.sb-link {
  display: flex; align-items: center; gap: 9px; padding: 8px 14px; margin: 0 8px;
  border-radius: var(--r-md); border: 1px solid transparent;
  color: var(--text-2); font-size: 12.5px; text-decoration: none; transition: all .2s;
}
.sb-link:hover {
  color: var(--text-1); background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.1);
  box-shadow: var(--shadow-sm); opacity: 1;
}
.sb-link.active {
  background: rgba(255,255,255,0.07);
  color: color-mix(in srgb, var(--cat, var(--brand)) 90%, white);
  border-color: color-mix(in srgb, var(--cat, var(--brand)) 30%, transparent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--cat, var(--brand)) 15%, transparent);
}
.sb-icon { width: 16px; height: 16px; display: flex; align-items: center; flex-shrink: 0; }
.sb-icon svg { width: 15px; height: 15px; color: color-mix(in srgb, var(--cat, var(--brand)) 70%, var(--text-3)); }
.sb-label { flex: 1; }
.sb-badge {
  font-size: 10px; font-weight: 700; font-family: var(--mono);
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.09);
  border-radius: 10px; padding: 1px 7px; color: var(--text-2); min-width: 26px; text-align: center;
}
.sb-badge-zero { color: var(--text-3); }
.sb-badge-brand { background: var(--brand-dim); border-color: var(--brand-border); color: var(--brand); }
.sb-digest { color: var(--brand); }
.sb-digest .sb-icon svg { color: var(--brand); }

.sidebar-footer {
  margin-top: auto; padding: 14px 22px 4px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex; flex-direction: column; gap: 7px;
}
.sf-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-3); }
.sf-row svg { width: 12px; height: 12px; }

/* ── Main ────────────────────────────────────────────────────────────────── */
.main-content { flex: 1; min-width: 0; padding: 24px 26px; display: flex; flex-direction: column; gap: 20px; }

/* ── Section panels (glass) ──────────────────────────────────────────────── */
.cat-section, .digest-section {
  background: rgb(10, 13, 28);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.cat-section    { border-top: 2px solid var(--cat); box-shadow: var(--shadow-md), var(--glass-inset), 0 0 40px color-mix(in srgb, var(--cat) 6%, transparent); }
.digest-section { border-top: 2px solid var(--brand); box-shadow: var(--shadow-md), var(--glass-inset), 0 0 40px var(--brand-glow); }

/* Section header */
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 15px 20px; cursor: pointer; user-select: none;
  transition: background .2s; gap: 12px;
}
.section-header:hover { background: rgba(255,255,255,0.03); }

.sh-left { display: flex; align-items: center; gap: 12px; }
.sh-icon-wrap {
  width: 38px; height: 38px; flex-shrink: 0;
  background: color-mix(in srgb, var(--cat, var(--brand)) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--cat, var(--brand)) 22%, transparent);
  border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center;
  color: var(--cat, var(--brand));
  box-shadow: 0 0 16px color-mix(in srgb, var(--cat, var(--brand)) 14%, transparent);
}
.sh-icon-wrap svg { width: 17px; height: 17px; }
.sh-icon-brand { background: var(--brand-dim); border-color: var(--brand-border); color: var(--brand); box-shadow: 0 0 16px var(--brand-glow); }

.sh-titles { display: flex; flex-direction: column; gap: 1px; }
.sh-eyebrow { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--brand); font-family: var(--mono); }
.sh-heading { font-size: 15px; font-weight: 700; color: var(--text-1); }
.sh-sub { font-size: 11px; color: var(--text-3); }

.sh-right { display: flex; align-items: center; gap: 10px; }
.sh-count {
  font-size: 11px; font-weight: 700; font-family: var(--mono);
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.09);
  border-radius: 20px; padding: 2px 10px; color: var(--text-2);
}
.sh-count-zero { color: var(--text-3); }

.collapse-btn {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: 1px solid transparent; border-radius: var(--r-md);
  color: var(--text-3); cursor: pointer; transition: all .2s; flex-shrink: 0;
}
.collapse-btn svg { width: 16px; height: 16px; transition: transform .3s cubic-bezier(.34,1.56,.64,1); }
.collapse-btn:hover { background: rgba(255,255,255,0.07); color: var(--text-1); border-color: rgba(255,255,255,0.1); }
.collapse-btn.collapsed svg { transform: rotate(-90deg); }

.section-body { padding: 16px 20px; }

/* ── Items grid ──────────────────────────────────────────────────────────── */
.items-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }
.no-items { font-size: 13px; color: var(--text-3); font-style: italic; padding: 4px 0; }

/* ── Item card ───────────────────────────────────────────────────────────── */
.item-card {
  /* Solid dark background — avoids backdrop-filter + transform blank-tile bug */
  background: rgb(14, 18, 38);
  border: 1px solid rgba(255,255,255,0.07);
  border-left: 3px solid rgba(255,255,255,0.08);
  border-radius: var(--r-lg); padding: 16px 17px;
  display: flex; flex-direction: column; gap: 9px;
  box-shadow: var(--shadow-sm);
  transition: transform .3s cubic-bezier(.34,1.56,.64,1), box-shadow .3s ease, border-color .2s ease, background .2s ease;
}
.item-card:hover {
  transform: translateY(-5px) scale(1.004);
  background: rgb(18, 23, 48);
  border-color: rgba(255,255,255,0.13);
  box-shadow: var(--shadow-lg);
}

/* Severity treatments */
.item-card.sev-critical {
  border-left-color: var(--critical);
  background: rgb(22, 12, 18);
  box-shadow: var(--shadow-sm), 0 0 20px var(--critical-glow);
}
.item-card.sev-critical:hover {
  box-shadow: var(--shadow-lg), 0 0 40px var(--critical-glow);
  border-color: rgba(244,63,94,0.35);
}
.item-card.sev-high {
  border-left-color: var(--high);
  background: rgb(20, 14, 10);
  box-shadow: var(--shadow-sm), 0 0 16px var(--high-glow);
}
.item-card.sev-high:hover {
  box-shadow: var(--shadow-lg), 0 0 32px var(--high-glow);
  border-color: rgba(249,115,22,0.32);
}

.card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.card-source {
  font-size: 10px; font-weight: 700; color: var(--brand); text-transform: uppercase;
  letter-spacing: .08em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%;
  background: rgba(0,200,150,0.07); border: 1px solid rgba(0,200,150,0.15);
  padding: 1px 7px; border-radius: 3px;
}
.item-card.sev-critical .card-source { color: #fca5a5; background: rgba(244,63,94,0.07); border-color: rgba(244,63,94,0.2); }
.item-card.sev-high    .card-source  { color: #fdba74; background: rgba(249,115,22,0.07); border-color: rgba(249,115,22,0.2); }
.card-time { font-size: 10px; color: var(--text-3); white-space: nowrap; font-family: var(--mono); }

.card-title { font-size: 14px; font-weight: 600; line-height: 1.5; }
.card-title a { color: var(--text-1); transition: color .15s; }
.card-title a:hover { color: var(--brand); opacity: 1; }

.card-summary { font-size: 12.5px; color: var(--text-2); line-height: 1.65; flex: 1; }
.card-footer { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }

/* Severity pills */
.sev-pill {
  font-size: 9.5px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase;
  padding: 2px 8px; border-radius: var(--r-sm); border: 1px solid; flex-shrink: 0;
}
.sev-pill-critical    { color: #fca5a5; background: rgba(244,63,94,.16);  border-color: rgba(244,63,94,.32); box-shadow: 0 0 8px rgba(244,63,94,.2); }
.sev-pill-high        { color: #fdba74; background: rgba(249,115,22,.16); border-color: rgba(249,115,22,.32); box-shadow: 0 0 8px rgba(249,115,22,.18); }
.sev-pill-interesting { color: var(--text-3); background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.08); }

/* CVSS badge */
.cvss-badge {
  font-size: 10px; font-weight: 700; font-family: var(--mono);
  color: #fde68a; background: rgba(234,179,8,.13); border: 1px solid rgba(234,179,8,.28);
  border-radius: var(--r-sm); padding: 2px 7px; box-shadow: 0 0 8px rgba(234,179,8,.15);
}

/* Read link */
.read-link {
  margin-left: auto; display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; color: var(--brand); white-space: nowrap;
  background: rgba(0,200,150,0.08); border: 1px solid rgba(0,200,150,0.2);
  padding: 3px 10px; border-radius: 4px;
  transition: background .15s, border-color .15s, color .15s;
}
.read-link svg { width: 11px; height: 11px; }
.read-link:hover { background: rgba(0,200,150,0.16); border-color: rgba(0,200,150,0.4); opacity: 1; }

/* CVE ID monospace */
.cve-id {
  font-family: var(--mono); font-size: 12px;
  color: var(--brand); background: var(--brand-dim);
  border: 1px solid var(--brand-border); border-radius: var(--r-sm); padding: 0 5px;
  box-shadow: 0 0 6px var(--brand-glow);
}

/* ── Weekly Digest ───────────────────────────────────────────────────────── */
.digest-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 14px; padding: 0 20px 20px;
}

.digest-card {
  background: rgb(14, 18, 38);
  border: 1px solid color-mix(in srgb, var(--dc) 20%, rgba(255,255,255,0.06));
  border-top: 2px solid var(--dc);
  border-radius: var(--r-lg); padding: 18px;
  display: flex; flex-direction: column; gap: 11px;
  box-shadow: var(--shadow-sm), 0 0 24px color-mix(in srgb, var(--dc) 8%, transparent);
  transition: transform .3s cubic-bezier(.34,1.56,.64,1), box-shadow .3s, border-color .2s;
}
.digest-card:hover {
  transform: translateY(-6px) scale(1.005);
  background: rgb(18, 23, 48);
  border-color: color-mix(in srgb, var(--dc) 50%, transparent);
  box-shadow: var(--shadow-lg), 0 0 48px color-mix(in srgb, var(--dc) 16%, transparent);
}
.digest-card-empty { opacity: .4; }

.dc-cat { display: flex; align-items: center; gap: 8px; }
.dc-icon {
  width: 28px; height: 28px; flex-shrink: 0;
  background: color-mix(in srgb, var(--dc) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--dc) 25%, transparent);
  border-radius: var(--r-sm);
  display: flex; align-items: center; justify-content: center; color: var(--dc);
  box-shadow: 0 0 10px color-mix(in srgb, var(--dc) 20%, transparent);
}
.dc-icon svg { width: 14px; height: 14px; }
.dc-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em;
  color: color-mix(in srgb, var(--dc) 90%, white);
}
.dc-title { font-size: 13.5px; font-weight: 600; line-height: 1.45; }
.dc-title a { color: var(--text-1); transition: color .15s; }
.dc-title a:hover { color: var(--brand); opacity: 1; }
.dc-summary { font-size: 12px; color: var(--text-2); line-height: 1.62; flex: 1; }
.dc-empty   { font-size: 12px; color: var(--text-3); font-style: italic; }
.dc-footer  { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.dc-source  { font-size: 10px; color: var(--text-3); }

/* ── Footer ──────────────────────────────────────────────────────────────── */
.site-footer {
  border-top: 1px solid rgba(255,255,255,0.06); padding: 22px 26px; margin-top: 4px;
  background: rgba(3,4,12,0.6); backdrop-filter: blur(16px);
}
.footer-inner { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.footer-brand { display: flex; align-items: center; gap: 6px; color: var(--brand); }
.footer-logo svg { width: 15px; height: 15px; }
.footer-name { font-family: var(--mono); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.footer-copy { font-size: 11px; color: var(--text-3); }

/* ── Search state ────────────────────────────────────────────────────────── */
.item-card.search-hidden, .digest-card.search-hidden { display: none; }

/* ── Scroll offset ───────────────────────────────────────────────────────── */
section { scroll-margin-top: calc(var(--topbar-h) + var(--header-h) + 12px); }

/* ── THREATCON bar ───────────────────────────────────────────────────────── */
.threatcon-bar {
  backdrop-filter: blur(12px);
  border-bottom: 1px solid;
  padding: 7px 22px; display: flex; align-items: center; gap: 10px; font-size: 12px;
  flex-wrap: wrap;
}
.tc-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.tc-dot-pulse { animation: blink 1.6s ease-in-out infinite; }
.tc-badge {
  font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .09em;
  border: 1px solid; border-radius: var(--r-sm); padding: 1px 7px; flex-shrink: 0;
}
.tc-level-name { font-family: var(--mono); font-size: 12px; font-weight: 800; letter-spacing: .06em; }
.tc-divider { color: var(--text-3); }
.tc-desc { color: var(--text-2); flex: 1; min-width: 0; }
.tc-scale { margin-left: auto; display: flex; gap: 4px; flex-shrink: 0; }
.tc-pip {
  width: 22px; height: 22px; border-radius: var(--r-sm);
  font-family: var(--mono); font-size: 9px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.05); color: var(--text-3);
  border: 1px solid rgba(255,255,255,0.07);
}
.tc-pip-active {
  color: #fff; font-weight: 800;
  animation: blink 1.6s ease-in-out infinite;
}

/* ── Trend delta ─────────────────────────────────────────────────────────── */
.tb-delta {
  font-family: var(--mono); font-size: 10px; font-weight: 700;
  padding: 1px 6px; border-radius: var(--r-sm); margin-left: 4px;
}
.tb-delta-up   { color: #fca5a5; background: rgba(244,63,94,.12); }
.tb-delta-down { color: #6ee7b7; background: rgba(0,200,150,.12); }
.tb-delta-flat { color: var(--text-3); background: rgba(255,255,255,.05); }

/* ── BREAKING tag ────────────────────────────────────────────────────────── */
.breaking-tag {
  font-family: var(--mono); font-size: 9px; font-weight: 800; letter-spacing: .1em;
  color: #fca5a5; background: rgba(244,63,94,.18); border: 1px solid rgba(244,63,94,.35);
  border-radius: var(--r-sm); padding: 1px 6px;
  animation: blink 1.4s ease-in-out infinite;
}

/* ── Top Stories / Lead Stories ──────────────────────────────────────────── */
.top-stories-section {
  background: rgb(10,13,28);
  border: 1px solid rgba(255,255,255,0.07);
  border-top: 2px solid var(--brand);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-md), var(--glass-inset), 0 0 48px var(--brand-glow);
  overflow: hidden;
}
.ts-header {
  display: flex; align-items: center; gap: 12px; padding: 15px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.ts-eyebrow {
  font-family: var(--mono); font-size: 10px; font-weight: 800; letter-spacing: .1em;
  color: var(--critical); animation: blink 1.6s ease-in-out infinite;
}
.ts-heading { font-size: 15px; font-weight: 700; color: var(--text-1); }
.ts-sub { font-size: 11px; color: var(--text-3); margin-left: 4px; }
.hero-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px; padding: 18px 20px;
}
.hero-card {
  background: rgb(14,18,38);
  border: 1px solid color-mix(in srgb, var(--hc) 18%, rgba(255,255,255,0.07));
  border-top: 2px solid var(--hc);
  border-radius: var(--r-lg); padding: 18px;
  display: flex; flex-direction: column; gap: 10px;
  box-shadow: var(--shadow-sm), 0 0 24px color-mix(in srgb, var(--hc) 8%, transparent);
  transition: transform .3s cubic-bezier(.34,1.56,.64,1), box-shadow .3s, border-color .2s;
}
.hero-card:hover {
  transform: translateY(-6px) scale(1.005);
  background: rgb(18,23,48);
  border-color: color-mix(in srgb, var(--hc) 50%, transparent);
  box-shadow: var(--shadow-lg), 0 0 48px color-mix(in srgb, var(--hc) 18%, transparent);
}
.hc-meta { display: flex; align-items: center; gap: 8px; }
.hc-cat-icon { width: 16px; height: 16px; display: flex; align-items: center; flex-shrink: 0; }
.hc-cat-icon svg { width: 14px; height: 14px; }
.hc-cat-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.hc-time { font-size: 10px; color: var(--text-3); font-family: var(--mono); margin-left: auto; }
.hc-title { font-size: 15px; font-weight: 700; line-height: 1.45; }
.hc-title a { color: var(--text-1); transition: color .15s; }
.hc-title a:hover { color: var(--brand); opacity: 1; }
.hc-summary { font-size: 12.5px; color: var(--text-2); line-height: 1.65; flex: 1; }
.hc-footer { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.hc-source { font-size: 10px; color: var(--text-3); margin-left: 4px; }

/* ── EPSS badge ──────────────────────────────────────────────────────────── */
.epss-badge {
  font-size: 9.5px; font-weight: 700; font-family: var(--mono); letter-spacing: .05em;
  padding: 2px 7px; border-radius: var(--r-sm); border: 1px solid; flex-shrink: 0;
}
.epss-high { color: #fdba74; background: rgba(249,115,22,.15); border-color: rgba(249,115,22,.35); box-shadow: 0 0 6px rgba(249,115,22,.2); }
.epss-med  { color: #fde68a; background: rgba(234,179,8,.12);  border-color: rgba(234,179,8,.28); }

/* ── KEV / Exploit badges ────────────────────────────────────────────────── */
.kev-badge {
  font-size: 9.5px; font-weight: 800; font-family: var(--mono); letter-spacing: .06em;
  color: #fca5a5; background: rgba(244,63,94,.18); border: 1px solid rgba(244,63,94,.4);
  border-radius: var(--r-sm); padding: 2px 8px; flex-shrink: 0;
  box-shadow: 0 0 8px rgba(244,63,94,.25);
}
.exploit-badge {
  font-size: 9.5px; font-weight: 700; font-family: var(--mono); letter-spacing: .05em;
  color: #fb923c; background: rgba(249,115,22,.14); border: 1px solid rgba(249,115,22,.32);
  border-radius: var(--r-sm); padding: 2px 8px; flex-shrink: 0;
}

/* ── Trending badges ─────────────────────────────────────────────────────── */
.trending-badge {
  font-size: 9.5px; font-weight: 700; font-family: var(--mono);
  color: var(--brand); background: var(--brand-dim); border: 1px solid var(--brand-border);
  border-radius: var(--r-sm); padding: 1px 7px; flex-shrink: 0;
}
.trending-badge.hot {
  color: #f97316; background: rgba(249,115,22,.1); border-color: rgba(249,115,22,.28);
  animation: blink 2s ease-in-out infinite;
}

/* ── Sidebar live/top badge ──────────────────────────────────────────────── */
.sb-badge-live {
  background: rgba(244,63,94,.14); border-color: rgba(244,63,94,.3); color: #fca5a5;
  animation: blink 1.6s ease-in-out infinite;
}
.sb-top { color: #fca5a5; }
.sb-top .sb-icon svg { color: #fca5a5; }

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 1024px) {
  .sidebar { display: none; }
  .header-nav { display: none; }
}
@media (max-width: 680px) {
  .header-inner { padding: 0 14px; gap: 12px; }
  .main-content { padding: 14px 12px; }
  .items-grid, .digest-grid { grid-template-columns: 1fr; }
  .topbar-updated { display: none; }
  .search-hint { display: none; }
}
"""

# ══ JS ═════════════════════════════════════════════════════════════════════════
_JS = """
'use strict';

// ── Collapsible sections ─────────────────────────────────────────────────────
document.querySelectorAll('[data-target]').forEach(el => {
  el.addEventListener('click', e => {
    if (e.target.closest('a')) return;
    const body = document.getElementById(el.dataset.target);
    if (!body) return;
    const btn    = el.querySelector('.collapse-btn');
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : '';
    if (btn) btn.classList.toggle('collapsed', isOpen);
  });
});

// ── Search ───────────────────────────────────────────────────────────────────
const searchInput = document.getElementById('search');
const clearBtn    = document.getElementById('clear-search');

function doSearch() {
  const q = searchInput.value.trim().toLowerCase();
  document.querySelectorAll('.searchable').forEach(card => {
    card.classList.toggle('search-hidden', q.length > 0 && !card.textContent.toLowerCase().includes(q));
  });
  document.querySelectorAll('.items-grid, .digest-grid').forEach(grid => {
    const visible = [...grid.querySelectorAll('.searchable')].filter(c => !c.classList.contains('search-hidden'));
    let msg = grid.querySelector('.search-no-results');
    if (q && visible.length === 0) {
      if (!msg) {
        msg = document.createElement('p');
        msg.className = 'no-items search-no-results';
        msg.textContent = 'No items match your search.';
        grid.appendChild(msg);
      }
    } else if (msg) {
      msg.remove();
    }
  });
}

searchInput.addEventListener('input', doSearch);
clearBtn.addEventListener('click', () => { searchInput.value = ''; doSearch(); searchInput.focus(); });

document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== searchInput) { e.preventDefault(); searchInput.focus(); }
  if (e.key === 'Escape' && document.activeElement === searchInput) { clearBtn.click(); searchInput.blur(); }
});

// ── Sidebar active state ─────────────────────────────────────────────────────
const sbLinks = document.querySelectorAll('.sb-link');
const io = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const id = entry.target.id;
      sbLinks.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + id));
    }
  });
}, { rootMargin: '-15% 0px -75% 0px' });

document.querySelectorAll('section[id]').forEach(s => io.observe(s));

// ── Hero grid search ─────────────────────────────────────────────────────────
const origSearch = doSearch;
searchInput.addEventListener('input', () => {
  document.querySelectorAll('.hero-grid').forEach(grid => {
    const q = searchInput.value.trim().toLowerCase();
    const visible = [...grid.querySelectorAll('.searchable')].filter(c => !c.classList.contains('search-hidden'));
    let msg = grid.querySelector('.search-no-results');
    if (q && visible.length === 0) {
      if (!msg) { msg = document.createElement('p'); msg.className = 'no-items search-no-results'; msg.textContent = 'No items match.'; grid.appendChild(msg); }
    } else if (msg) { msg.remove(); }
  });
});
"""
