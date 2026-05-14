"""
The Tax Express — Auto-Update Bot
Runs every 3 hours via GitHub Actions.
Fetches latest tax news from ITAT, CBDT, CBIC, and tax news portals.
Updates news.json → triggers Cloudflare Pages auto-deploy.
"""

import feedparser
import json
import re
import hashlib
import textwrap
from datetime import datetime, timezone

# ── RSS / Atom feeds from reliable public tax sources ────────
FEEDS = [
    {
        "url": "https://taxguru.in/feed/",
        "source": "Tax Guru",
        "category_map": {
            "income-tax":             "it",
            "tds":                    "it",
            "transfer-pricing":       "it",
            "goods-and-service-tax":  "gst",
            "gst":                    "gst",
            "itat":                   "itat",
            "income-tax-appellate":   "itat",
            "supreme-court":          "court",
            "high-court":             "court",
            "budget":                 "it",
        },
        "default_category": "it",
    },
    {
        "url": "https://itatonline.org/feed/",
        "source": "ITAT Online",
        "category_map": {},
        "default_category": "itat",
    },
    {
        "url": "https://www.taxmann.com/research/rss/news.xml",
        "source": "Taxmann",
        "category_map": {
            "gst":           "gst",
            "income-tax":    "it",
            "itat":          "itat",
            "high court":    "court",
            "supreme court": "court",
        },
        "default_category": "it",
    },
    {
        "url": "https://www.incometaxindia.gov.in/Lists/Latest%20Updates/Rss.aspx",
        "source": "Income Tax Dept",
        "category_map": {},
        "default_category": "it",
    },
    {
        "url": "https://taxclick.in/feed/",
        "source": "TaxClick",
        "category_map": {
            "gst":            "gst",
            "income-tax":     "it",
            "itat":           "itat",
            "high court":     "court",
            "supreme court":  "court",
        },
        "default_category": "it",
    },
    {
        "url": "https://caclubindia.com/news/rss.asp",
        "source": "CA Club India",
        "category_map": {
            "gst":         "gst",
            "income tax":  "it",
            "itat":        "itat",
            "high court":  "court",
        },
        "default_category": "it",
    },
]

# ── Helpers ──────────────────────────────────────────────────
def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def make_id(title: str) -> str:
    return "tte_" + hashlib.md5(title.encode("utf-8")).hexdigest()[:10]

def parse_date(entry) -> str:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def detect_category(entry, feed_cfg: dict) -> str:
    tags = []
    if hasattr(entry, "tags"):
        tags = [t.term.lower() for t in entry.tags]
    if hasattr(entry, "category"):
        tags.append(str(entry.category).lower())
    title_lower = (entry.get("title", "")).lower()
    for keyword, cat in feed_cfg["category_map"].items():
        if keyword in tags or keyword in title_lower:
            return cat
    return feed_cfg["default_category"]

def get_full_content(entry) -> str:
    """Return the richest available text content from a feed entry."""
    # Try content (Atom) — may be full HTML
    if hasattr(entry, "content") and entry.content:
        for c in entry.content:
            val = c.get("value", "")
            if val and len(val) > 200:
                return val
    # Try summary
    if hasattr(entry, "summary") and entry.summary:
        return entry.summary
    return ""

def build_body_html(title: str, raw_content: str, source: str, category: str) -> str:
    """
    Convert raw RSS content (HTML or plain text) into a clean article body
    for The Tax Express story reader modal.
    Tries to preserve any real HTML paragraphs; falls back to auto-formatting
    plain text into structured sections.
    """
    # If raw_content already has substantial HTML paragraph tags, clean & return
    plain = strip_html(raw_content)
    has_html_paras = bool(re.search(r"<p[^>]*>", raw_content, re.IGNORECASE))

    if has_html_paras and len(plain) > 300:
        # Strip everything except safe tags
        safe = re.sub(r"<(?!/?(?:p|h[2-6]|strong|em|b|i|ul|ol|li|br)(?:\s[^>]*)?)([^>]+)>",
                      "", raw_content)
        safe = re.sub(r"\s{2,}", " ", safe).strip()
        return safe

    # Plain-text path — split into sentences and build structured HTML
    if len(plain) < 60:
        plain = title

    # Break into ~3 paragraphs intelligently
    sentences = re.split(r'(?<=[.!?])\s+', plain)
    chunks = []
    current = []
    char_count = 0
    target = max(200, len(plain) // 3)

    for s in sentences:
        current.append(s)
        char_count += len(s)
        if char_count >= target and len(chunks) < 2:
            chunks.append(" ".join(current))
            current = []
            char_count = 0
    if current:
        chunks.append(" ".join(current))

    # Assign section headings by category
    heading_map = {
        "it":    ["Background", "Key Development", "Implications"],
        "gst":   ["Background", "Key Decision / Circular", "Compliance Impact"],
        "itat":  ["Background & Facts", "Issue Before the Tribunal", "Held"],
        "court": ["Background & Facts", "Issue Before the Court", "Court's Ruling"],
    }
    headings = heading_map.get(category, ["Background", "Update", "Significance"])

    parts = []
    for i, chunk in enumerate(chunks):
        heading = headings[i] if i < len(headings) else "Further Detail"
        parts.append(f"<h3>{heading}</h3><p>{chunk.strip()}</p>")

    return "\n".join(parts)

def load_news(path="news.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_updated": "", "items": []}

def save_news(data: dict, path="news.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── Main ─────────────────────────────────────────────────────
def main():
    existing   = load_news()
    seen_ids   = {item["id"] for item in existing.get("items", [])}
    new_items  = []

    for feed_cfg in FEEDS:
        print(f"Fetching: {feed_cfg['url']}")
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:15]:
                title    = strip_html(entry.get("title", "")).strip()
                if not title or len(title) < 10:
                    continue

                item_id = make_id(title)
                # Also check plain md5 (old format without tte_ prefix)
                plain_id = hashlib.md5(title.encode("utf-8")).hexdigest()[:10]
                if item_id in seen_ids or plain_id in seen_ids:
                    continue

                category  = detect_category(entry, feed_cfg)
                raw       = get_full_content(entry)
                plain_sum = strip_html(raw)[:480].strip()
                if plain_sum and not plain_sum.endswith((".", "…")):
                    plain_sum = plain_sum.rsplit(" ", 1)[0] + "…"

                body_html = build_body_html(title, raw, feed_cfg["source"], category)

                item = {
                    "id":       item_id,
                    "date":     parse_date(entry),
                    "category": category,
                    "title":    title,
                    "summary":  plain_sum or title,
                    "source":   feed_cfg["source"],
                    "url":      entry.get("link", "#"),
                    "body":     body_html,
                }
                new_items.append(item)
                seen_ids.add(item_id)
                print(f"  + [{item['category'].upper()}] {title[:72]}")

        except Exception as exc:
            print(f"  ERROR fetching {feed_cfg['url']}: {exc}")

    if new_items:
        # Newest first; keep latest 120 total
        all_items = new_items + existing.get("items", [])
        all_items.sort(key=lambda x: x["date"], reverse=True)
        existing["items"]        = all_items[:120]
        existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        save_news(existing)
        print(f"\nDone — added {len(new_items)} new item(s). Total: {len(existing['items'])}")
    else:
        # Still update the timestamp so users see "last checked" time
        existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        save_news(existing)
        print("\nNo new items found. Timestamp updated.")

if __name__ == "__main__":
    main()
