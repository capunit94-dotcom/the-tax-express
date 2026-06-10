"""
Tax Bench — Auto-Update Bot
Runs every 3 hours via GitHub Actions.
Fetches latest tax news from RSS feeds, then uses Claude AI to write
full 500-700 word editorial articles for each new item.
Updates news.json → triggers Cloudflare Pages auto-deploy.
"""

import feedparser
import json
import re
import hashlib
import os
from datetime import datetime, timezone

# ── RSS / Atom feeds ──────────────────────────────────────────
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
        "url": "https://taxclick.in/feed/",
        "source": "TaxClick",
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

# ── Helpers ───────────────────────────────────────────────────
def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()

def make_id(title):
    return "tte_" + hashlib.md5(title.encode("utf-8")).hexdigest()[:10]

def parse_date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def detect_category(entry, feed_cfg):
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

def get_rss_content(entry):
    if hasattr(entry, "content") and entry.content:
        for c in entry.content:
            val = c.get("value", "")
            if val and len(val) > 200:
                return val
    if hasattr(entry, "summary") and entry.summary:
        return entry.summary
    return ""

def get_rss_image(entry, raw_content=""):
    """Extract the best image URL from an RSS entry."""
    # 1. media:content or media:thumbnail tags
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            url = m.get("url", "")
            if url and url.startswith("http") and any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", "image"]):
                return url
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url", "")
        if url and url.startswith("http"):
            return url
    # 2. enclosure (podcast-style image attachment)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", "")
    # 3. First <img> tag in the content HTML
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_content or "")
    if img_match:
        url = img_match.group(1)
        if url.startswith("http"):
            return url
    return ""

# ── AI Editorial Generator ────────────────────────────────────
def generate_editorial(title, summary, category, api_key):
    """
    Call Groq API (Llama 3.3 70B) to write a full editorial article.
    Returns HTML string with h3/p tags.
    Falls back to basic body if API unavailable.
    Get free key at: https://console.groq.com/
    """
    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        cat_context = {
            "itat":  "ITAT (Income Tax Appellate Tribunal) judgment",
            "court": "High Court or Supreme Court tax ruling",
            "gst":   "GST / indirect tax development, circular, or ruling",
            "it":    "income tax notification, circular, amendment, or CBDT development",
        }.get(category, "Indian tax development")

        section_guide = {
            "itat": [
                "Background",
                "Facts of the Case",
                "Issue Before the Tribunal",
                "Arguments Raised",
                "Tribunal's Decision",
                "Implications for Taxpayers",
            ],
            "court": [
                "Background",
                "Facts of the Case",
                "Issue Before the Court",
                "Arguments and Legal Provisions",
                "Court's Ruling",
                "Implications for Taxpayers",
            ],
            "gst": [
                "Background",
                "What Was Issued",
                "Key Provisions and Clarifications",
                "Analysis",
                "Compliance Impact",
            ],
            "it": [
                "Background",
                "What Was Notified or Decided",
                "Key Provisions",
                "Analysis",
                "Implications for Taxpayers",
            ],
        }.get(category, [
            "Background",
            "Key Development",
            "Analysis",
            "Implications for Taxpayers",
        ])

        sections_str = "\n".join(f"  <h3>{s}</h3>" for s in section_guide)

        prompt = f"""You are the Chief Tax Correspondent of Tax Bench — India's most authoritative tax intelligence publication, read exclusively by senior Chartered Accountants, tax advocates, and CFOs. Your writing is the gold standard for Indian tax journalism: rigorous, insightful, and deeply grounded in statute and case law.

Your task: Write a premium, publication-ready editorial (700–900 words) on the following {cat_context}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARTICLE TITLE: {title}
NEWS BRIEF: {strip_html(summary)[:700]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY STRUCTURE — use these exact HTML headings in order:
{sections_str}

WRITING STANDARDS (non-negotiable):

1. DEPTH & ANALYSIS: Each section must contain 2–3 rich paragraphs. Go beyond summarising — analyse the significance, the legal reasoning, and the real-world impact.

2. LEGAL PRECISION: Cite specific, real sections of the Income Tax Act 2025/1961, CGST Act 2017, established Supreme Court/High Court precedents, and CBDT/CBIC circulars relevant as background. Name actual legal provisions (e.g., "Section 9(1) of the CGST Act", "Section 145A of the Income Tax Act").

3. STRICT FACT DISCIPLINE: Do NOT invent case citation numbers, circular numbers, or notification numbers unless explicitly stated in the NEWS BRIEF. Refer generically if unknown (e.g., "the impugned order", "this circular"). You MUST use real background law and landmark precedents.

4. PRACTITIONER FOCUS: The final section must deliver 4–5 concrete, numbered action points that a CA or tax lawyer can act on immediately — filing steps, documentation requirements, risk areas, or advisory tips.

5. TONE: Authoritative, active voice. Avoid clichés like "it is pertinent to note". Write as a legal expert to a peer.

6. Do NOT reference Tax Guru, Taxmann, ITAT Online, or any third-party publication.

OUTPUT: Return ONLY the article body HTML using <h3> and <p> tags. No preamble, no title, no byline, no markdown, no code fences. Start directly with the first <h3> tag.
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a senior Indian tax journalist. Write detailed, legally precise editorial articles in HTML format using only <h3> and <p> tags."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.65,
        )
        html = response.choices[0].message.content.strip()
        html = re.sub(r"```html?\s*", "", html)
        html = re.sub(r"```\s*$",     "", html).strip()
        print(f"    ✓ Grok-3 editorial generated ({len(html)} chars)")
        return html

    except ImportError:
        print("    ✗ openai not installed — using basic body")
        return _basic_body(title, summary, category)
    except Exception as e:
        print(f"    ✗ Gemini API error: {e} — using basic body")
        return _basic_body(title, summary, category)


def _basic_body(title, plain, category):
    """Fallback: split plain text into headed sections."""
    sentences = re.split(r'(?<=[.!?])\s+', strip_html(plain) or title)
    chunks, cur, n = [], [], 0
    for s in sentences:
        cur.append(s)
        n += len(s)
        if n >= max(180, len(strip_html(plain)) // 3) and len(chunks) < 2:
            chunks.append(" ".join(cur)); cur = []; n = 0
    if cur:
        chunks.append(" ".join(cur))
    heads = {
        "it":    ["Background", "Key Development", "Implications"],
        "gst":   ["Background", "Key Decision", "Compliance Impact"],
        "itat":  ["Background & Facts", "Issue Before the Tribunal", "Held"],
        "court": ["Background & Facts", "Issue Before the Court", "Court's Ruling"],
    }.get(category, ["Background", "Update", "Significance"])
    return "\n".join(
        f"<h3>{heads[i] if i < len(heads) else 'Further Detail'}</h3><p>{c.strip()}</p>"
        for i, c in enumerate(chunks)
    )


# ── File I/O ──────────────────────────────────────────────────
def load_news(path="news.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_updated": "", "items": []}

def save_news(data, path="news.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────
def main():
    api_key    = os.environ.get("GROQ_API_KEY", "")
    use_ai     = bool(api_key)
    if use_ai:
        print("Groq AI editorial generation: ENABLED (Llama 3.3 70B — enhanced prompt)")
    else:
        print("Groq AI editorial generation: DISABLED (add GROQ_API_KEY to GitHub secrets)")

    existing  = load_news()
    seen_ids  = {item["id"] for item in existing.get("items", [])}
    # Also index old-format IDs (plain md5 without tte_ prefix)
    seen_ids |= {
        hashlib.md5(item.get("title","").encode()).hexdigest()[:10]
        for item in existing.get("items", [])
    }

    new_items = []
    ai_count  = 0
    AI_LIMIT  = 0   # updater.py no longer generates editorials — regenerate.py
                    # handles that with its MAX_REGEN cap to stay under 100K TPD

    for feed_cfg in FEEDS:
        print(f"\nFetching: {feed_cfg['url']}")
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:20]:
                title = strip_html(entry.get("title", "")).strip()
                if not title or len(title) < 10:
                    continue

                item_id  = make_id(title)
                plain_id = hashlib.md5(title.encode("utf-8")).hexdigest()[:10]
                if item_id in seen_ids or plain_id in seen_ids:
                    continue

                category  = detect_category(entry, feed_cfg)
                raw       = get_rss_content(entry)
                image_url = get_rss_image(entry, raw)
                plain_sum = strip_html(raw)[:480].strip()
                if plain_sum and not plain_sum.endswith((".", "…")):
                    plain_sum = plain_sum.rsplit(" ", 1)[0] + "…"

                print(f"  + [{category.upper()}] {title[:70]}")

                # Generate AI editorial — regenerate.py will fill gaps at 6 AM
                # Use _basic_body only as a temporary placeholder (< 800 chars,
                # no full <h3> structure) so regenerate.py detects and rewrites it.
                if use_ai and ai_count < AI_LIMIT:
                    body_html = generate_editorial(title, plain_sum or title, category, api_key)
                    ai_count += 1
                else:
                    # Short placeholder — regenerate.py scheduled job will rewrite this
                    body_html = f"<p>{plain_sum or title}</p>"

                new_items.append({
                    "id":       item_id,
                    "date":     parse_date(entry),
                    "category": category,
                    "title":    title,
                    "summary":  plain_sum or title,
                    "source":   "Tax Bench",   # original editorial, not external source
                    "url":      entry.get("link", "#"),
                    "image":    image_url,
                    "body":     body_html,
                })
                seen_ids.add(item_id)

        except Exception as exc:
            print(f"  ERROR: {exc}")

    if new_items:
        all_items = new_items + existing.get("items", [])
        all_items.sort(key=lambda x: x["date"], reverse=True)
        existing["items"]        = all_items[:120]
        existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        save_news(existing)
        ai_note = f" ({ai_count} AI-generated)" if use_ai else ""
        print(f"\nDone — added {len(new_items)} new article(s){ai_note}. Total: {len(existing['items'])}")
    else:
        existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        save_news(existing)
        print("\nNo new items found. Timestamp updated.")


if __name__ == "__main__":
    main()
