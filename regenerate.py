"""
The Tax Express — One-time AI Editorial Regeneration
Rewrites body field of visible items in news.json using xAI Grok-3.
Run via GitHub Actions: Actions > Regenerate All Articles with AI Editorials > Run workflow

Quota-aware: exits early if quota is exhausted (5 consecutive errors).
Saves progress to disk every 10 articles so partial work is never lost.
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone

SAVE_EVERY        = 10   # write news.json to disk after every N successes
MAX_CONSEC_ERRORS = 5    # abort if this many consecutive 429/errors in a row
VISIBLE_SLOTS     = 16   # lead(1) + secondary(2) + three-col(3) + live-feed(10)
                         # items[16+] are in "Show More" — skip them

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
4. STRICT RULE — Do NOT invent or fabricate ANY specific facts not present in the TITLE or BRIEF above. This means:
   - Do NOT invent circular numbers, notification numbers, or case citation numbers unless they appear in the title/brief
   - Do NOT invent specific dates, deadlines, or monetary amounts not mentioned
   - Do NOT invent names of parties in a case not mentioned
   - If a specific detail is unknown, refer to it generically (e.g. "this circular", "the ruling in question", "the court held")
5. You MAY and SHOULD draw on your knowledge of Indian tax law to provide legal context: cite real sections of the CGST Act, Income Tax Act, relevant established case law, and CBDT/CBIC circulars that form the BACKGROUND to this topic — not the specific development being reported.
6. Do NOT reference "Tax Guru", "Taxmann", "ITAT Online" or any third-party publication. Write as The Tax Express original editorial.
7. The "Implications for Taxpayers" section must give concrete, actionable guidance for CAs and taxpayers.
8. Return ONLY the article body HTML (h3 and p tags). No preamble, no title, no byline, no markdown fences.
"""
    response = client.chat.completions.create(
        model="grok-3",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1800,
        temperature=0.7,
    )
    html = response.choices[0].message.content.strip()
    html = re.sub(r"```html?\s*", "", html)
    html = re.sub(r"```\s*$", "", html).strip()
    return html


def save_progress(data, items):
    """Write current state to disk (no git commit — just preserve progress)."""
    data["items"]        = items
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        print("ERROR: XAI_API_KEY not set")
        return

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    with open("news.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    items            = data.get("items", [])
    updated          = 0
    errors           = 0
    consec_errors    = 0   # consecutive failures — quota exhaustion detector
    quota_exhausted  = False

    force = os.environ.get("FORCE_REGEN", "").lower() in ("1", "true", "yes")
    visible_items = items[:VISIBLE_SLOTS]

    need_regen = list(range(len(visible_items))) if force else [
        i for i, x in enumerate(visible_items)
        if not (len(x.get("body","")) > 800 and "<h3>" in x.get("body",""))
    ]

    print(f"Total articles : {len(items)}")
    print(f"Visible slots  : {VISIBLE_SLOTS} (lead + secondary + three-col + live feed)")
    print(f"Show More skip : {max(0, len(items) - VISIBLE_SLOTS)} articles (items[{VISIBLE_SLOTS}+] — not regenerated)")
    print(f"Force regen    : {'YES — rewriting all visible articles' if force else 'NO — skipping already-done'}")
    print(f"Need editorials: {len(need_regen)}")
    print(f"Already done   : {VISIBLE_SLOTS - len(need_regen)}")
    print("Starting Grok-3 regeneration (visible articles only)...\n")

    for i, item in enumerate(visible_items):
        title    = item.get("title", "")
        summary  = item.get("summary", "") or item.get("body", "")
        category = item.get("category", "it")

        print(f"[{i+1}/{VISIBLE_SLOTS}] {title[:65]}")

        # Skip articles already having a full AI-generated body (unless force mode)
        existing_body = item.get("body", "")
        if not force and len(existing_body) > 800 and "<h3>" in existing_body:
            print(f"  ↷ Already done ({len(existing_body)} chars) — skipping")
            consec_errors = 0   # reset streak on skip (not a failure)
            continue

        # Retry up to 3 times with exponential backoff on rate limit errors
        success = False
        for attempt in range(3):
            try:
                body = generate_editorial(title, summary, category, client)
                item["body"]   = body
                item["source"] = "The Tax Express"
                updated       += 1
                consec_errors  = 0
                print(f"  ✓ {len(body)} chars generated")
                success = True
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = 60 * (attempt + 1)   # 60s, then 120s
                    print(f"  ⚠ Rate limited — waiting {wait}s (attempt {attempt+2}/3)...")
                    time.sleep(wait)
                else:
                    errors       += 1
                    consec_errors += 1
                    print(f"  ✗ Error: {e}")
                    break

        # Save progress to disk every SAVE_EVERY successes
        if updated > 0 and updated % SAVE_EVERY == 0:
            save_progress(data, items)
            print(f"  💾 Progress saved ({updated} articles done so far)")

        # Abort early if quota appears exhausted
        if consec_errors >= MAX_CONSEC_ERRORS:
            print(f"\n⛔ {MAX_CONSEC_ERRORS} consecutive failures — Gemini daily quota likely exhausted.")
            print(   "   Saving progress and exiting. Re-run after quota resets (midnight UTC).")
            quota_exhausted = True
            break

        # 4 seconds between requests = 15 RPM (well under 30 RPM Groq free limit)
        if i < VISIBLE_SLOTS - 1:
            time.sleep(4)

    # ── Final save + merge with remote ───────────────────────────────────────
    save_progress(data, items)

    # Merge with remote to preserve articles added during the long run
    try:
        subprocess.run(["git", "fetch", "origin", "main"], capture_output=True)
        remote_raw = subprocess.check_output(
            ["git", "show", "origin/main:news.json"], stderr=subprocess.DEVNULL
        ).decode("utf-8")
        remote_data = json.loads(remote_raw)

        # Map of article IDs that now have full AI editorials
        regen_map = {
            item["id"]: item["body"]
            for item in items
            if item.get("body") and len(item.get("body", "")) > 800 and "<h3>" in item.get("body", "")
        }

        # Apply regenerated bodies onto the remote's article list
        merge_count = 0
        for ritem in remote_data["items"]:
            if ritem["id"] in regen_map:
                ritem["body"]   = regen_map[ritem["id"]]
                ritem["source"] = "The Tax Express"
                merge_count     += 1

        remote_data["last_updated"] = data["last_updated"]
        data = remote_data
        print(f"\nMerged {merge_count} regenerated bodies onto {len(data['items'])} remote articles.")
    except Exception as e:
        print(f"\nCould not merge with remote ({e}) — saving local data only.")

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    status = "⛔ QUOTA EXHAUSTED — re-run tomorrow" if quota_exhausted else "✅ Complete"
    print(f"\n{status} — {updated} regenerated, {errors} errors.")


if __name__ == "__main__":
    main()
