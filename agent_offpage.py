#!/usr/bin/env python3
"""
Sigma SEO Agent — Off-Page Autopilot
--------------------------------------
Runs on a schedule. Each run:
  1. Picks one already-built calculator (from built_calculators.json) to
     promote, rotating through the list
  2. Uses Claude + web search to find REAL, specific prospects (resource pages,
     roundup posts, relevant blogs) that could plausibly link to that page
  3. Drafts a short, non-spammy outreach email for each prospect
  4. Saves everything to outreach_drafts/<date>.md for you to review

IMPORTANT — read this once:
No tool (this one included) can actually create a backlink on someone else's
website without a human on that site approving it. This script does NOT send
anything automatically — sending real cold email at scale without review is
also how you get your domain flagged as spam. It gives you a ready-to-send,
reviewed-in-30-seconds draft instead.

If you want automatic SENDING later, that needs a one-time Gmail API OAuth
setup (Google Cloud project + consent screen) — ask and it can be added.
For now: paste the drafts into a chat with Claude and it can send them
through your connected Gmail with a quick confirmation per email.

Required environment variables:
  ANTHROPIC_API_KEY
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

BASE_DIR = os.path.dirname(__file__)
TRACKING_FILE = os.path.join(BASE_DIR, "built_calculators.json")
DRAFTS_DIR = os.path.join(BASE_DIR, "outreach_drafts")
ROTATION_FILE = os.path.join(BASE_DIR, "offpage_rotation.json")


def call_claude(system, user, max_tokens=2000, tools=None):
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if tools:
        payload["tools"] = tools

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(text_blocks).strip()


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def pick_page_to_promote():
    tracking = load_json(TRACKING_FILE, {"calculators": []})
    calculators = tracking.get("calculators", [])
    if not calculators:
        raise ValueError("No calculators tracked yet in built_calculators.json")

    rotation = load_json(ROTATION_FILE, {"last_index": -1})
    next_index = (rotation["last_index"] + 1) % len(calculators)
    save_json(ROTATION_FILE, {"last_index": next_index})
    return calculators[next_index]


def find_prospects_and_draft(page):
    system = (
        "You are a realistic, white-hat digital PR / off-page SEO strategist. "
        "Use web search to find ACTUAL pages/sites that could plausibly link to "
        "this tool — not generic categories. Be specific: real site names or real "
        "page types you found. Never suggest spammy directories or link farms. "
        "For each prospect, write a short (under 130 words), human-sounding, "
        "non-hypey outreach email. No markdown fences in the output."
    )
    user = f"""Page to promote:
Name: {page['name']}
URL: {page.get('wp_link', '(not yet live)')}
Primary keyword: {page['primary_keyword']}

Find 5 realistic, specific link prospects (e.g. actual resource pages, roundup
articles, or relevant blogs you found via search) for this page's niche.

For each prospect give:
### Prospect N: [site/page name + what it is]
**Why it fits:** one line
**Outreach email:**
Subject: ...
Body: ...
"""
    return call_claude(
        system,
        user,
        max_tokens=2500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )


def main():
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting off-page autopilot run...")

    page = pick_page_to_promote()
    print(f"Promoting: {page['name']}")

    draft_content = find_prospects_and_draft(page)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = os.path.join(DRAFTS_DIR, f"{today}-{page['slug']}.md")
    with open(out_path, "w") as f:
        f.write(f"# Off-page outreach draft — {page['name']}\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(draft_content)
        f.write("\n\n---\nReview above, then either send manually or paste into a chat "
                "with Claude to send via your connected Gmail (with confirmation).\n")

    print(f"Draft saved to {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
