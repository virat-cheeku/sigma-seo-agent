#!/usr/bin/env python3
"""
Sigma SEO Agent — On-Page Autopilot
------------------------------------
Runs on a schedule (via GitHub Actions). Each run:
  1. Loads the list of calculators already built (built_calculators.json)
  2. Asks Claude (with web search) to find ONE new, high-opportunity calculator
     idea not yet built, based on search demand + low competition
  3. Asks Claude to generate the FULL page (HTML/CSS/JS + JSON-LD schema +
     blog content + FAQ) matching the existing sigmacalculator.net design system
  4. Publishes it to WordPress via the REST API as a DRAFT (safe default —
     you review and hit Publish yourself until you trust the pipeline)
  5. Updates built_calculators.json and commits it (done by the GitHub Action)

Required environment variables (set as GitHub Secrets):
  ANTHROPIC_API_KEY   - your Anthropic API key
  WP_URL              - e.g. https://sigmacalculator.net
  WP_USER             - your WordPress username
  WP_APP_PASSWORD     - a WordPress "Application Password" (NOT your login password)
  WP_POST_TYPE        - optional, defaults to "pages". Use a custom post type slug
                         if your theme/builder needs one (e.g. "tools")
  PUBLISH_STATUS      - optional, defaults to "draft". Set to "publish" once trusted.
"""

import os
import sys
import json
import re
import requests
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
WP_URL = os.environ["WP_URL"].rstrip("/")
WP_USER = os.environ["WP_USER"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
WP_POST_TYPE = os.environ.get("WP_POST_TYPE", "pages")
PUBLISH_STATUS = os.environ.get("PUBLISH_STATUS", "draft")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

TRACKING_FILE = os.path.join(os.path.dirname(__file__), "built_calculators.json")

DESIGN_SYSTEM_PROMPT = """
You are building a page for sigmacalculator.net, a suite of free online calculator
tools. Follow this exact established design system:

- Single standalone HTML file, no external framework, inline <style> and <script>
- White background, primary accent color #1c5ce0 (blue), font: 'Inter' from Google Fonts
- Rounded cards (border-radius ~14-16px), soft shadows, generous whitespace
- NO site header or footer — this page is embedded into the theme's blank/canvas
  template, so start directly with the page content (H1 + calculator tool)
- Fully mobile-responsive (test down to 360px width)
- Semantic heading hierarchy: one H1, logical H2/H3 structure
- A working, fully functional calculator (real JS logic, not a placeholder)
- Below the calculator: a rich blog-style content section (600-900 words) explaining
  the concept, how the calculation works, and practical use cases
- An FAQ section (5-6 questions) formatted as an accordion
- Embedded JSON-LD schema in <script type="application/ld+json">: a @graph containing
  WebPage, WebApplication (applicationCategory: UtilitiesApplication,
  isAccessibleForFree: true), and FAQPage matching the FAQ section content
- Clean, accessible markup (labels for inputs, aria attributes where relevant)

Output ONLY the complete HTML file content. No explanation, no markdown fences.
"""


def call_claude(system, user, max_tokens=1500, tools=None):
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


def load_built_list():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {"calculators": []}


def save_built_list(data):
    with open(TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def pick_new_calculator_idea(already_built):
    system = (
        "You are an SEO strategist for a free online calculator tools site. "
        "Use web search to find real, current search-demand signals. Be concrete, "
        "not generic. Respond with ONLY a JSON object, no other text, no markdown fences."
    )
    user = f"""Already-built calculators on this site (do NOT repeat any of these):
{json.dumps(already_built, indent=2)}

Find ONE new calculator idea that:
- Has real search demand (education, health/fitness, personal finance, everyday utility niches)
- Is NOT already in the list above
- Is realistic to build as a single-page client-side JS calculator
- Has a plausible, achievable ranking opportunity (not dominated only by huge sites like
  Omni Calculator / Calculator.net on the exact long-tail keyword)

Return JSON with exactly these keys:
{{
  "name": "Human readable tool name",
  "slug": "url-safe-slug",
  "primary_keyword": "main target keyword",
  "secondary_keywords": ["kw1", "kw2", "kw3"],
  "rationale": "1-2 sentences on why this is a good opportunity right now"
}}"""

    result = call_claude(
        system,
        user,
        max_tokens=800,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )
    # extract JSON even if the model wraps it in prose/fences by mistake
    match = re.search(r"\{.*\}", result, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse idea JSON from model output:\n{result}")
    return json.loads(match.group(0))


def generate_page_html(idea):
    user = f"""Build the full calculator page for:

Name: {idea['name']}
Primary keyword: {idea['primary_keyword']}
Secondary keywords: {', '.join(idea.get('secondary_keywords', []))}
Page URL: {WP_URL}/{idea['slug']}/

Follow the design system exactly."""
    html = call_claude(DESIGN_SYSTEM_PROMPT, user, max_tokens=8000)
    # strip stray markdown fences if the model adds them despite instructions
    html = re.sub(r"^```(?:html)?\s*", "", html.strip())
    html = re.sub(r"\s*```$", "", html.strip())
    return html


def publish_to_wordpress(idea, html_content):
    endpoint = f"{WP_URL}/wp-json/wp/v2/{WP_POST_TYPE}"
    payload = {
        "title": idea["name"],
        "slug": idea["slug"],
        "status": PUBLISH_STATUS,
        "content": html_content,
    }
    resp = requests.post(
        endpoint,
        auth=(WP_USER, WP_APP_PASSWORD),
        json=payload,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"WordPress publish failed [{resp.status_code}]: {resp.text[:500]}")
    return resp.json()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting on-page autopilot run...")

    tracking = load_built_list()
    already_built = tracking["calculators"]

    print("Researching new calculator opportunity...")
    idea = pick_new_calculator_idea(already_built)
    print(f"Chosen idea: {idea['name']} ({idea['primary_keyword']})")
    print(f"Rationale: {idea.get('rationale', '')}")

    print("Generating full page HTML...")
    html = generate_page_html(idea)
    print(f"Generated {len(html)} characters of HTML.")

    print(f"Publishing to WordPress as '{PUBLISH_STATUS}'...")
    wp_response = publish_to_wordpress(idea, html)
    wp_link = wp_response.get("link", "(no link returned)")
    print(f"Published: {wp_link}")

    already_built.append(
        {
            "name": idea["name"],
            "slug": idea["slug"],
            "primary_keyword": idea["primary_keyword"],
            "wp_id": wp_response.get("id"),
            "wp_link": wp_link,
            "status": PUBLISH_STATUS,
            "created": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_built_list({"calculators": already_built})
    print("Tracking file updated. Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
