"""
Tax Axis — One-time AI Editorial Regeneration
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
        "gst":   "GST / indirect tax development, notification, circular, or ruling",
        "it":    "income tax notification, circular, amendment, or CBDT/CBIC development",
    }.get(category, "Indian tax law development")

    section_guide = {
        "itat":  ["Background & Legal Framework", "Facts of the Case",
                  "Issue Before the Tribunal", "Arguments & Contentions",
                  "Tribunal's Ruling & Reasoning", "Key Takeaways for Practitioners"],
        "court": ["Background & Legal Framework", "Facts of the Case",
                  "Issue Before the Court", "Arguments & Legal Provisions",
                  "Court's Decision & Reasoning", "Key Takeaways for Practitioners"],
        "gst":   ["Background & Statutory Framework", "The Development in Detail",
                  "Key Provisions & Clarifications", "Critical Analysis",
                  "Compliance Implications & Action Points"],
        "it":    ["Background & Statutory Framework", "The Development in Detail",
                  "Key Provisions & Impact", "Critical Analysis",
                  "Compliance Implications & Action Points"],
    }.get(category, ["Background & Framework", "The Development",
                     "Legal Analysis", "Key Takeaways for Practitioners"])

    sections_str = "\n".join(f"  <h3>{s}</h3>" for s in section_guide)

    prompt = f"""You are the Chief Tax Correspondent of Tax Axis — India's most authoritative tax intelligence publication, read exclusively by senior Chartered Accountants, tax advocates, and CFOs. Your writing is the gold standard for Indian tax journalism: rigorous, insightful, and deeply grounded in statute and case law.

Your task: Write a premium, publication-ready editorial (700–900 words) on the following {cat_context}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARTICLE TITLE: {title}
NEWS BRIEF: {strip_html(summary)[:700]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANDATORY STRUCTURE — use these exact HTML headings in order:
{sections_str}

WRITING STANDARDS (non-negotiable):

1. DEPTH & ANALYSIS: Each section must contain 2–3 rich paragraphs. Go beyond summarising — analyse the significance, the legal reasoning, and the real-world impact. Ask "why does this matter?" and answer it.

2. LEGAL PRECISION: Cite specific, real sections of the Income Tax Act 2025/1961, CGST Act 2017, IGST Act, established Supreme Court/High Court precedents, and CBDT/CBIC circulars that are GENUINELY relevant as background and context. Name actual legal provisions (e.g., "Section 9(1) of the CGST Act", "Section 145A of the Income Tax Act"). This is what separates Tax Axis from generic publications.

3. STRICT FACT DISCIPLINE: Do NOT invent case citation numbers, circular numbers, or notification numbers unless explicitly stated in the NEWS BRIEF above. Refer to them generically if unknown (e.g., "the impugned order", "this circular", "the tribunal held"). You may and MUST use real background law and landmark precedents.

4. PRACTITIONER FOCUS: The final section "Key Takeaways for Practitioners" must deliver 4–5 concrete, numbered action points that a CA or tax lawyer can act on immediately — filing deadlines, compliance steps, documentation requirements, risk areas, or advisory tips.

5. TONE & VOICE: Authoritative yet accessible. Use active voice. Avoid clichés like "it is pertinent to note" or "it is worth mentioning". Write as a legal expert explaining to a peer, not a student summarising for a teacher.

6. EXCLUSIVITY: Never reference Tax Guru, Taxmann, ITAT Online, or any third-party publication. This is original Tax Express journalism.

OUTPUT: Return ONLY the article body HTML using <h3> and <p> tags. No preamble, no title tag, no byline, no markdown, no code fences. Start directly with the first <h3> tag.
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
    html = re.sub(r"```\s*$", "", html).strip()
    return html


def save_progress(data, items):
    """Write current state to disk (no git commit — just preserve progress)."""
    data["items"]        = items
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set")
        return

    from groq import Groq
    client = Groq(api_key=api_key)

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
                item["source"] = "Tax Axis"
                updated       += 1
                consec_errors  = 0
                print(f"  ✓ {len(body)} chars generated")
                success = True
                break
            except Exception as e:
                err_str = str(e)
                print(f"  ✗ Attempt {attempt+1}/3 failed: {err_str[:300]}")
                if "429" in err_str and attempt < 2:
                    wait = 60 * (attempt + 1)   # 60s, then 120s
                    print(f"  ⚠ Rate limited — waiting {wait}s...")
                    time.sleep(wait)
                else:
                    errors       += 1
                    consec_errors += 1
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
                ritem["source"] = "Tax Axis"
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
