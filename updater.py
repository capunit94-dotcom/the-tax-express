"""
The Tax Express — Auto-Update Bot
Runs daily via GitHub Actions.
Fetches latest tax news from ITAT, CBDT, CBIC, and tax news portals.
Updates news.json → triggers Cloudflare Pages auto-deploy.
"""

import feedparser
import json
import re
import hashlib
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
            "gst":          "gst",
            "income-tax":   "it",
            "itat":         "itat",
            "high court":   "court",
            "supreme court":"court",
        },
        "default_category": "it",
    },
]

# ── Helpers ──────────────────────────────────────────────────
def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def make_id(title: str) -> str:
    return hashlib.md5(title.encode("utf-8")).hexdigest()[:10]

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
    title_lower = (entry.title or "").lower()
    for keyword, cat in feed_cfg["category_map"].items():
        if keyword in tags or keyword in title_lower:
            return cat
    return feed_cfg["default_category"]

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
                item_id = make_id(entry.get("title", ""))
                if item_id in seen_ids:
                    continue

                # Build summary — prefer summary, fall back to content
                raw_summary = ""
                if hasattr(entry, "summary"):
                    raw_summary = entry.summary
                elif hasattr(entry, "content") and entry.content:
                    raw_summary = entry.content[0].get("value", "")
                summary = strip_html(raw_summary)[:450].strip()
                if summary and not summary.endswith("."):
                    summary = summary.rsplit(" ", 1)[0] + "…"

                item = {
                    "id":       item_id,
                    "date":     parse_date(entry),
                    "category": detect_category(entry, feed_cfg),
                    "title":    strip_html(entry.get("title", "No Title")),
                    "summary":  summary,
                    "source":   feed_cfg["source"],
                    "url":      entry.get("link", "#"),
                }
                new_items.append(item)
                seen_ids.add(item_id)
                print(f"  + [{item['category'].upper()}] {item['title'][:70]}")

        except Exception as exc:
            print(f"  ERROR fetching {feed_cfg['url']}: {exc}")

    if new_items:
        # Newest first; keep latest 120 total
        all_items = new_items + existing.get("items", [])
        all_items.sort(key=lambda x: x["date"], reverse=True)
        existing["items"]        = all_items[:120]
        existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_news(existing)
        print(f"\nDone — added {len(new_items)} new item(s). Total: {len(existing['items'])}")
    else:
        print("\nNo new items found today.")

if __name__ == "__main__":
    main()
