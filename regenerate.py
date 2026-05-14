"""
The Tax Express — One-time AI Editorial Regeneration
Rewrites body field of ALL items in news.json using Google Gemini.
Run via GitHub Actions: Actions > Regenerate All Articles with AI Editorials > Run workflow
"""

import json
import os
import re
import time
from datetime import datetime, timezone

def strip_html(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()

def generate_editorial(title, summary, category, client):
    cat_context = {
        "itat":  "ITAT (Income Tax Appellate Tribunal) judgment",
        "court": "High Court or Supreme Court tax ruling",
        "gst":   "GST / indirect tax development, circular, or ruling",
        "it":    "income tax notification, circular, amendment, or CBDT development",
    }.get(category, "Indian tax development")

    section_guide = {
        "itat":  ["Background", "Facts of the Case", "Issue Before the Tribunal",
                  "Arguments Raised", "Tribunal's Decision", "Implications for Taxpayers"],
        "court": ["Background", "Facts of the Case", "Issue Before the Court",
                  "Arguments and Legal Provisions", "Court's Ruling", "Implications for Taxpayers"],
        "gst":   ["Background", "What Was Issued", "Key Provisions and Clarifications",
                  "Analysis", "Compliance Impact"],
        "it":    ["Background", "What Was Notified or Decided", "Key Provisions",
                  "Analysis", "Implications for Taxpayers"],
    }.get(category, ["Background", "Key Development", "Analysis", "Implications for Taxpayers"])

    sections_str = "\n".join(f"- <h3>{s}</h3>" for s in section_guide)

    prompt = f"""You are a senior tax journalist and legal analyst writing for The Tax Express — India's premier tax intelligence platform read by chartered accountants, tax advocates, and finance professionals.

Write a comprehensive, authoritative editorial article (550–750 words) about the following {cat_context}:

TITLE: {title}

BRIEF: {strip_html(summary)[:600]}

INSTRUCTIONS:
1. Write in a professional Indian tax journalism style — factual, precise, and insightful.
2. Use these exact HTML section headings in this order:
{sections_str}
3. Each section must have at least 2 substantive paragraphs using <p> tags.
4. Draw on your knowledge of Indian income tax law, GST law, and judicial precedents. Mention relevant sections of the Act, earlier case law, or CBDT/CBIC circulars where appropriate.
5. Do NOT reference "Tax Guru", "Taxmann", "ITAT Online" or any third-party publication. Write as The Tax Express original editorial.
6. Do NOT say "it is reported that" or "according to sources". Write authoritatively.
7. The "Implications for Taxpayers" section must give concrete, actionable guidance for CAs and taxpayers.
8. Return ONLY the article body HTML (h3 and p tags). No preamble, no title, no byline, no markdown fences.
"""
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    html = response.text.strip()
    html = re.sub(r"```html?\s*", "", html)
    html = re.sub(r"```\s*$", "", html).strip()
    return html


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        return

    from google import genai
    client = genai.Client(api_key=api_key)

    with open("news.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    items   = data.get("items", [])
    updated = 0
    errors  = 0

    print(f"Total articles: {len(items)}")
    print("Regenerating all with Gemini AI editorials...\n")

    for i, item in enumerate(items):
        title    = item.get("title", "")
        summary  = item.get("summary", "") or item.get("body", "")
        category = item.get("category", "it")

        print(f"[{i+1}/{len(items)}] {title[:65]}")

        # Retry up to 3 times with exponential backoff on rate limit errors
        success = False
        for attempt in range(3):
            try:
                body = generate_editorial(title, summary, category, client)
                item["body"]   = body
                item["source"] = "The Tax Express"
                updated += 1
                print(f"  ✓ {len(body)} chars generated")
                success = True
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = 60 * (attempt + 1)   # 60s, then 120s
                    print(f"  ⚠ Rate limited — waiting {wait}s before retry {attempt+2}/3...")
                    time.sleep(wait)
                else:
                    errors += 1
                    print(f"  ✗ Error: {e}")
                    break

        # 6 seconds between requests = 10 RPM (well under 15 RPM free limit)
        if i < len(items) - 1:
            time.sleep(6)

    data["items"]        = items
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone — {updated} articles regenerated, {errors} errors.")


if __name__ == "__main__":
    main()
