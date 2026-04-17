#!/usr/bin/env python3
"""
AI categorisation, relevance filtering, and summarisation via Claude.

Falls back to keyword-based processing when no API key is present.
Items are batched (BATCH_SIZE per call) to minimise API cost.

Cache: processed results are saved to summary_cache.json so subsequent
runs only call Claude for new URLs never seen before.
"""

import re
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.ai")

# ── Cache file ─────────────────────────────────────────────────────────────────
CACHE_FILE  = Path(__file__).parent / "summary_cache.json"
CACHE_TTL_D = 14   # evict entries older than this many days

# ── Rolling items store (7-day window) ─────────────────────────────────────────
STORE_FILE  = Path(__file__).parent / "items_store.json"
STORE_TTL_D = 7

# ── Category definitions ───────────────────────────────────────────────────────
CATEGORIES = {
    "cve_vuln":            "Breaking CVEs & Vulnerabilities",
    "cloud_security":      "Cloud Security",
    "ai_llm_security":     "AI / LLM Security",
    "threat_intel":        "Threat Intel & APTs",
    "offensive_defensive": "Offensive & Defensive Security",
    "product_launches":    "New Security Products",
    "new_notable":         "New & Notable",
}

# ── Keyword fallback map ───────────────────────────────────────────────────────
_KW: dict = {
    "cve_vuln": [
        "cve-", "cvss", "vulnerability", "vulnerabilities", "exploit", "exploited",
        "rce", "remote code execution", "sql injection", "xss", "buffer overflow",
        "zero-day", "0day", "patch tuesday", "security update", "advisory",
        "memory corruption", "use-after-free", "privilege escalation", "cisa",
        "known exploited", "nvd", "national vulnerability",
    ],
    "cloud_security": [
        "aws", "azure", "gcp", "google cloud", "s3 bucket", "iam role",
        "kubernetes", "k8s", "container security", "docker", "eks", "aks", "gke",
        "cloud misconfiguration", "saas", "sspm", "casb", "terraform",
        "lambda", "serverless", "cloud storage", "blob storage",
    ],
    "ai_llm_security": [
        "llm", "large language model", "gpt", "chatgpt", "gemini", "copilot",
        "ai security", "prompt injection", "jailbreak", "model poisoning",
        "adversarial", "ai attack", "rag attack", "vector database",
        "ai supply chain", "foundation model", "alignment risk",
        "ai red team", "model extraction",
    ],
    "threat_intel": [
        "apt", "nation-state", "ransomware", "malware", "ioc", "indicator",
        "threat actor", "campaign", "lazarus", "sandworm", "cozy bear",
        "fancy bear", "volt typhoon", "salt typhoon", "dark web", "botnet",
        "c2 server", "command and control", "espionage", "state-sponsored",
        "threat intelligence", "ttp", "mitre att", "data breach", "data leak",
    ],
    "offensive_defensive": [
        "pentest", "penetration test", "red team", "blue team", "purple team",
        "detection bypass", "edr bypass", "evasion", "siem", "xdr", "soar",
        "incident response", "threat hunting", "forensics", "ctf", "payload",
        "exploit development", "post-exploitation", "lateral movement",
        "privilege escalation", "offensive security", "cobalt strike",
    ],
    "product_launches": [
        "launches", "announces", "introduces", "unveils", "releases",
        "new product", "new platform", "new solution", "new service",
        "series a", "series b", "funding", "raises", "startup",
        "general availability", "ga release", "now available",
        "platform launch", "product release", "vendor", "company",
    ],
    "new_notable": [
        "open source", "github", "new tool", "tool release", "framework release",
        "research paper", "arxiv", "whitepaper", "proof of concept",
        "open-sourced", "significant", "breakthrough",
    ],
}

BATCH_SIZE = 12   # items per Claude API call
API_DELAY  = 0.5  # seconds between API calls


# ══ Items store helpers ════════════════════════════════════════════════════════

def _load_store() -> dict:
    """Load persisted items from previous runs, keyed by URL, evicting >7 days."""
    if not STORE_FILE.exists():
        return {}
    try:
        data = json.loads(STORE_FILE.read_text(encoding="utf-8"))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=STORE_TTL_D)).isoformat()
        evicted = [url for url, v in data.items() if v.get("stored_at", "") < cutoff]
        for url in evicted:
            del data[url]
        return data
    except Exception as exc:
        logger.warning("  Items store load failed (%s) — starting fresh", exc)
        return {}


def _save_store(store: dict) -> None:
    try:
        STORE_FILE.write_text(json.dumps(store, default=str, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("  Items store save failed: %s", exc)


def _merge_into_store(store: dict, raw_items: list) -> list:
    """Add new items to store and return full 7-day item list."""
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in raw_items:
        url = item.get("url")
        if not url or url in store:
            continue
        entry = {k: v for k, v in item.items() if k != "published_dt"}
        pub = item.get("published_dt")
        entry["published_dt_iso"] = pub.isoformat() if pub else None
        entry["stored_at"] = now_iso
        store[url] = entry
    _save_store(store)

    # Reconstruct item list from store for 7-day window
    result = []
    for url, entry in store.items():
        item = {k: v for k, v in entry.items() if k not in ("stored_at", "published_dt_iso")}
        item["url"] = url
        iso = entry.get("published_dt_iso")
        if iso:
            try:
                dt = datetime.fromisoformat(iso)
                item["published_dt"] = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                item["published_dt"] = None
        result.append(item)
    return result


# ══ Cache helpers ══════════════════════════════════════════════════════════════

def _load_cache() -> dict:
    """
    Load the on-disk cache.
    Structure: { url: { "summary": str, "severity": str, "category": str,
                         "include": bool, "cached_at": iso-str } }
    Evicts entries older than CACHE_TTL_D days on load.
    """
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_D)).isoformat()
        evicted = [url for url, v in data.items() if v.get("cached_at", "") < cutoff]
        for url in evicted:
            del data[url]
        if evicted:
            logger.debug("  Cache: evicted %d stale entries", len(evicted))
        return data
    except Exception as exc:
        logger.warning("  Cache load failed (%s) — starting fresh", exc)
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("  Cache save failed: %s", exc)


# ══ Public entry point ═════════════════════════════════════════════════════════

def process_all_items(
    raw_items: list,
    github_repos: list,
    api_key: Optional[str],
) -> dict:
    """
    Categorise, filter, and summarise all items.
    Returns a data dict consumed by dashboard_generator.
    """
    now        = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d  = now - timedelta(days=7)

    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    items_24h    = [i for i in raw_items if _aware(i.get("published_dt")) and _aware(i["published_dt"]) >= cutoff_24h]
    items_no_date = [i for i in raw_items if not i.get("published_dt")]
    items_24h    = items_24h + items_no_date

    # Build 7-day items from the rolling store (persisted across daily runs)
    store    = _load_store()
    all_7d   = _merge_into_store(store, raw_items)
    items_7d = [i for i in all_7d if _aware(i.get("published_dt")) and _aware(i["published_dt"]) >= cutoff_7d]

    logger.info("  24h items: %d | 7-day items: %d (from store) | no-date items: %d",
                len(items_24h), len(items_7d), len(items_no_date))

    # Load cache — used regardless of whether we have an API key
    cache = _load_cache()
    cache_hits = sum(1 for i in items_24h if i.get("url") in cache)
    new_items  = [i for i in items_24h if i.get("url") not in cache]
    logger.info("  Cache: %d hits | %d new items to process", cache_hits, len(new_items))

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            # Only call Claude for items not already in cache
            if new_items:
                new_results = _ai_process(new_items, client)
                # Persist new results into cache
                ts = now.isoformat()
                for cat_items in new_results.values():
                    for item in cat_items:
                        url = item.get("url")
                        if url:
                            cache[url] = {
                                "summary":   item.get("summary", ""),
                                "severity":  item.get("severity", "Interesting"),
                                "category":  item.get("category", "new_notable"),
                                "include":   item.get("include", True),
                                "cached_at": ts,
                            }
                # Also cache excluded items so we don't reprocess them
                for item in new_items:
                    if item.get("url") and item["url"] not in cache:
                        cache[item["url"]] = {
                            "summary":   item.get("description", ""),
                            "severity":  item.get("severity_hint", "Interesting"),
                            "category":  _kw_guess_category(item),
                            "include":   False,
                            "cached_at": ts,
                        }
                _save_cache(cache)
            else:
                new_results = {k: [] for k in CATEGORIES}

            # Merge cached results into the output
            categories = _merge_with_cache(items_24h, new_results, cache)
            weekly_digest = _ai_weekly_digest(items_7d, categories, client)
            notable_repos = _ai_process_github(github_repos, client)
            logger.info("  AI processing complete")
        except Exception as exc:
            logger.error("  AI processing failed (%s) — using keyword fallback", exc)
            categories    = _kw_categorise(items_24h)
            weekly_digest = _kw_digest(items_7d)
            notable_repos = _format_github_fallback(github_repos)
    else:
        logger.info("  No API key — keyword-based categorisation")
        categories    = _kw_categorise(items_24h)
        weekly_digest = _kw_digest(items_7d)
        notable_repos = _format_github_fallback(github_repos)

    categories.setdefault("new_notable", [])
    categories["new_notable"] = notable_repos + categories["new_notable"]

    total_categorised = sum(len(v) for v in categories.values())
    return {
        "categories":    categories,
        "weekly_digest": weekly_digest,
        "generated_at":  now.isoformat(),
        "total_raw":     len(raw_items),
        "total_shown":   total_categorised,
        "github_count":  len(github_repos),
    }


def _merge_with_cache(items_24h: list, new_results: dict, cache: dict) -> dict:
    """
    Build the final categorised dict by combining:
    - Items freshly processed by Claude (already in new_results)
    - Items whose results come from cache
    """
    # Start with what Claude just processed
    categorised: dict = {k: list(v) for k, v in new_results.items()}

    for item in items_24h:
        url = item.get("url")
        if not url or url not in cache:
            continue
        cached = cache[url]
        if not cached.get("include", True):
            continue
        cat = cached.get("category") or _kw_guess_category(item)
        if cat not in categorised:
            cat = "new_notable"
        # Avoid duplicates (item may already be in new_results)
        existing_urls = {i.get("url") for i in categorised[cat]}
        if url in existing_urls:
            continue
        categorised[cat].append({
            **item,
            "summary":  cached.get("summary") or item.get("description", ""),
            "severity": cached.get("severity", "Interesting"),
            "category": cat,
            "include":  True,
        })

    return categorised


# ══ AI processing ══════════════════════════════════════════════════════════════

def _ai_process(items: list, client) -> dict:
    """Send items to Claude in batches; return categorised+summarised dict."""
    categorised: dict = {k: [] for k in CATEGORIES}

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        try:
            results = _call_claude_batch(batch, client)
            for item, result in zip(batch, results):
                if not result.get("include"):
                    continue
                cat = result.get("category")
                if cat not in categorised:
                    cat = _kw_guess_category(item)
                categorised[cat].append({
                    **item,
                    "summary":  result.get("summary") or item.get("description", ""),
                    "severity": result.get("severity", "Interesting"),
                    "category": cat,
                    "include":  True,
                })
        except Exception as exc:
            logger.warning("  Batch %d failed: %s — keyword fallback for batch", i // BATCH_SIZE, exc)
            for item in batch:
                cat = _kw_guess_category(item)
                categorised[cat].append({
                    **item,
                    "summary":  item.get("description", item["title"]),
                    "severity": item.get("severity_hint", "Interesting"),
                    "category": cat,
                    "include":  True,
                })
        time.sleep(API_DELAY)

    return categorised


def _call_claude_batch(items: list, client) -> list:
    payload = [
        {
            "index":       idx,
            "title":       item["title"],
            "description": (item.get("description") or "")[:400],
            "source":      item["source"],
        }
        for idx, item in enumerate(items)
    ]

    prompt = f"""You are a senior cybersecurity intelligence analyst. Analyse these {len(items)} security news items.

For each item:
1. Decide whether to include it — exclude low-signal marketing, job postings, and non-security content.
2. If included, assign ONE category:
   - cve_vuln          -> CVEs, vulnerabilities, patches, exploits, security advisories
   - cloud_security    -> AWS/Azure/GCP/SaaS security, cloud misconfigs, container/K8s security
   - ai_llm_security   -> AI/ML attacks, prompt injection, LLM security, AI supply chain risks
   - threat_intel      -> APT groups, ransomware campaigns, IOCs, malware, nation-state activity
   - offensive_defensive -> pentesting tools, red/blue team techniques, detections, bypasses
   - product_launches  -> new commercial security products, vendor launches, startup funding rounds, platform GA releases
   - new_notable       -> significant new open-source tools, research papers, academic findings
3. Assign severity:
   - Critical    -> active exploitation, immediate risk, CVSS >=9, nation-state breach
   - High        -> significant vulnerability or credible threat, CVSS 7-9, major campaign
   - Interesting -> good practitioner signal, new technique, useful tool
4. Write a 2-3 sentence practitioner summary — direct, technical, zero fluff.

Return ONLY a JSON array (no markdown fences, no commentary), one object per input item in the same order:
[
  {{"include": true, "category": "cve_vuln", "severity": "Critical", "summary": "..."}},
  {{"include": false, "category": null, "severity": null, "summary": null}}
]

Items to analyse:
{json.dumps(payload, indent=2)}"""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = resp.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    parsed = json.loads(text)
    if not isinstance(parsed, list) or len(parsed) != len(items):
        raise ValueError(f"Unexpected response shape: got {len(parsed)} items, expected {len(items)}")
    return parsed


def _ai_weekly_digest(items_7d: list, categories_24h: dict, client) -> dict:
    all_cat_items = []
    for cat, cat_items in categories_24h.items():
        if cat == "new_notable":
            continue
        all_cat_items.extend(cat_items)

    combined = {i["url"]: i for i in all_cat_items}
    for item in items_7d:
        if item["url"] not in combined and item.get("category_hint"):
            combined[item["url"]] = {
                **item,
                "summary":  item.get("description", ""),
                "severity": item.get("severity_hint", "Interesting"),
                "category": item.get("category_hint"),
            }
    candidate_items = list(combined.values())[:80]

    if len(candidate_items) < 3:
        return _empty_digest()

    payload = [
        {
            "title":    i["title"],
            "source":   i["source"],
            "url":      i["url"],
            "category": i.get("category") or i.get("category_hint", "unknown"),
            "summary":  (i.get("summary") or i.get("description", ""))[:300],
        }
        for i in candidate_items
    ]

    prompt = f"""You are a senior cybersecurity analyst curating a weekly digest for practitioners.

From these {len(payload)} items spanning the past 7 days, select the SINGLE most significant story for each of these 5 categories:
- cve_vuln, cloud_security, ai_llm_security, threat_intel, offensive_defensive

Choose the item with the broadest real-world impact, urgency, or practitioner relevance.
Write a 3-4 sentence executive summary that explains WHAT happened and WHY it matters.

Return ONLY valid JSON (no markdown), with exactly this structure:
{{
  "cve_vuln":            {{"title": "...", "source": "...", "url": "...", "summary": "..."}},
  "cloud_security":      {{"title": "...", "source": "...", "url": "...", "summary": "..."}},
  "ai_llm_security":     {{"title": "...", "source": "...", "url": "...", "summary": "..."}},
  "threat_intel":        {{"title": "...", "source": "...", "url": "...", "summary": "..."}},
  "offensive_defensive": {{"title": "...", "source": "...", "url": "...", "summary": "..."}}
}}

Items available:
{json.dumps(payload, indent=2)}"""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        digest = json.loads(text)
        for cat in ("cve_vuln", "cloud_security", "ai_llm_security", "threat_intel", "offensive_defensive"):
            digest.setdefault(cat, None)
        return digest
    except Exception as exc:
        logger.warning("  Weekly digest AI call failed: %s", exc)
        return _empty_digest()


def _ai_process_github(repos: list, client) -> list:
    if not repos:
        return []

    payload = [
        {
            "index":       idx,
            "name":        r["name"],
            "description": r["description"][:200],
            "stars":       r["stars"],
            "language":    r["language"],
            "topics":      r["topics"][:8],
        }
        for idx, r in enumerate(repos)
    ]

    prompt = f"""You are a security researcher evaluating new GitHub repositories.

From these {len(payload)} repos (all recently created, security-related), select up to 8 that are most worth a practitioner's attention — think PentAGI-level significance: novel offensive/defensive tools, important research projects, or libraries that fill a real gap.

For each selected repo, write a 2-sentence practitioner summary explaining what it does and why it matters.

Return ONLY a JSON array (no markdown):
[
  {{"index": 0, "include": true, "summary": "..."}},
  {{"index": 1, "include": false, "summary": null}}
]

Repos:
{json.dumps(payload, indent=2)}"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        results = json.loads(text)

        enriched = []
        for r in results:
            if not r.get("include"):
                continue
            idx = r["index"]
            if 0 <= idx < len(repos):
                enriched.append({
                    **repos[idx],
                    "summary":  r.get("summary") or repos[idx]["description"],
                    "severity": "Interesting",
                    "category": "new_notable",
                    "include":  True,
                })
        return enriched
    except Exception as exc:
        logger.warning("  GitHub AI processing failed: %s — using raw repos", exc)
        return _format_github_fallback(repos[:8])


# ══ Keyword fallback ═══════════════════════════════════════════════════════════

def _kw_guess_category(item: dict) -> str:
    if item.get("category_hint"):
        return item["category_hint"]
    text = (item.get("title", "") + " " + item.get("description", "")).lower()
    scores = {cat: 0 for cat in _KW}
    for cat, keywords in _KW.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else "new_notable"


def _kw_categorise(items: list) -> dict:
    categorised: dict = {k: [] for k in CATEGORIES}
    for item in items:
        cat = _kw_guess_category(item)
        categorised[cat].append({
            **item,
            "summary":  item.get("description") or item["title"],
            "severity": item.get("severity_hint", "Interesting"),
            "category": cat,
            "include":  True,
        })
    return categorised


def _kw_digest(items_7d: list) -> dict:
    digest = {}
    categorised = _kw_categorise(items_7d)
    for cat in ("cve_vuln", "cloud_security", "ai_llm_security", "threat_intel", "offensive_defensive"):
        cat_items = categorised.get(cat, [])

        def _sort_key(i):
            sev = i.get("severity", "Interesting")
            order = {"Critical": 0, "High": 1, "Interesting": 2}.get(sev, 2)
            dt = i.get("published_dt") or datetime.min.replace(tzinfo=timezone.utc)
            return (order, -dt.timestamp())

        cat_items.sort(key=_sort_key)
        if cat_items:
            top = cat_items[0]
            digest[cat] = {
                "title":   top["title"],
                "source":  top["source"],
                "url":     top["url"],
                "summary": top.get("summary") or top.get("description", ""),
            }
        else:
            digest[cat] = None
    return digest


def _empty_digest() -> dict:
    return {cat: None for cat in
            ("cve_vuln", "cloud_security", "ai_llm_security", "threat_intel", "offensive_defensive")}


def _format_github_fallback(repos: list) -> list:
    return [
        {
            **r,
            "summary":  r.get("description") or "New security repository.",
            "severity": "Interesting",
            "category": "new_notable",
            "include":  True,
        }
        for r in repos[:10]
    ]
