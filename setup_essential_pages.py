#!/usr/bin/env python3
"""
Sigma SEO Agent — Essential Pages Setup (run ONCE, not on a schedule)
------------------------------------------------------------------------
Generates and publishes the 3 pages Google AdSense requires before approval:
  - Privacy Policy
  - About Us
  - Contact Us

These publish as DRAFTS like everything else — review and adjust the
specifics (especially Privacy Policy details: what data you actually
collect, any contact form, your business name/location) before publishing.

IMPORTANT: This is a starting draft, not legal advice. AdSense/privacy law
requirements can vary by your audience's location (e.g. GDPR for EU visitors,
CCPA for California). Have a real look before it goes live, and adjust the
placeholders (site owner name, contact email, etc.) marked with [BRACKETS].

Required environment variables: same as agent_publish.py
  ANTHROPIC_API_KEY, WP_URL, WP_USER, WP_APP_PASSWORD, WP_POST_TYPE (optional)
"""

import os
import sys
import requests

def require_env(name):
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"MISSING SECRET: '{name}' is not set (or empty).", file=sys.stderr)
        sys.exit(1)
    return val

ANTHROPIC_API_KEY = require_env("ANTHROPIC_API_KEY")
WP_URL = require_env("WP_URL").rstrip("/")
WP_USER = require_env("WP_USER")
WP_APP_PASSWORD = require_env("WP_APP_PASSWORD")
WP_POST_TYPE = os.environ.get("WP_POST_TYPE", "pages").strip() or "pages"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"

SITE_NAME = os.environ.get("SITE_NAME", "Sigma Calculator")
SITE_URL = WP_URL
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "[YOUR-CONTACT-EMAIL]")

DESIGN_NOTE = """
Match the site's existing design system: white background, blue accent
(#1c5ce0), Inter font, rounded cards, no header/footer (page is embedded
into a blank/canvas template), mobile responsive, clean semantic HTML
(one H1, logical H2 structure). Output ONLY the HTML content for inside
the page body — no <html>/<head> wrapper, no markdown fences.
"""


def call_claude(system, user, max_tokens=3000):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Claude API error [{resp.status_code}]: {resp.text[:800]}")
    data = resp.json()
    return "\n".join(b["text"] for b in data.get("content", []) if b.get("type") == "text").strip()


def publish_page(title, slug, html_content):
    endpoint = f"{WP_URL}/wp-json/wp/v2/{WP_POST_TYPE}"
    resp = requests.post(
        endpoint,
        auth=(WP_USER, WP_APP_PASSWORD),
        json={"title": title, "slug": slug, "status": "draft", "content": html_content},
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"WordPress publish failed [{resp.status_code}]: {resp.text[:500]}")
    return resp.json()


def build_privacy_policy():
    system = "You write clear, compliant privacy policy pages for small websites. Include placeholders in [BRACKETS] for anything site-specific you don't know. Cover: what data is collected (forms, analytics, cookies), use of Google AdSense/Google Analytics (third-party cookies, personalized ads, opt-out via Google Ads Settings), children's privacy (site not directed at under-13s), data retention, user rights (access/deletion requests), contact info, and a 'last updated' date placeholder. Note plainly this is a template, not legal advice." + DESIGN_NOTE
    user = f"""Site name: {SITE_NAME}
Site URL: {SITE_URL}
Contact email: {CONTACT_EMAIL}
Site type: free online calculator tools (no user accounts, no payments)

Write the full Privacy Policy page."""
    return call_claude(system, user)


def build_about_us():
    system = "You write genuine, trustworthy 'About Us' pages for niche tool websites -- the kind that helps both users and AdSense reviewers understand who is behind the site and why it exists. Avoid generic corporate fluff. Mention the mission (free, accurate, easy-to-use calculators), how the tools are built/verified, and a bit of personality." + DESIGN_NOTE
    user = f"""Site name: {SITE_NAME}
Site URL: {SITE_URL}
Site type: a free suite of online calculator tools spanning education, health, and finance categories.

Write the full About Us page."""
    return call_claude(system, user)


def build_contact_us():
    system = "You write short, clear 'Contact Us' pages. Include the contact email prominently, expected response time, and what kind of inquiries are welcome (bug reports, tool suggestions, business inquiries). Include a simple HTML contact form (name, email, message fields) using a POST to '#' as a placeholder action -- note in a code comment that the form action needs to be wired to the site's actual form handler (e.g. WPForms, Contact Form 7, or a mailto fallback)." + DESIGN_NOTE
    user = f"""Site name: {SITE_NAME}
Contact email: {CONTACT_EMAIL}

Write the full Contact Us page."""
    return call_claude(system, user)


def main():
    pages = [
        ("Privacy Policy", "privacy-policy", build_privacy_policy),
        ("About Us", "about-us", build_about_us),
        ("Contact Us", "contact-us", build_contact_us),
    ]
    for title, slug, builder in pages:
        print(f"Generating {title}...")
        html = builder()
        print(f"Publishing {title} as draft...")
        result = publish_page(title, slug, html)
        print(f"  -> {result.get('link', '(no link)')}")
    print("\nDone. Review each draft in WordPress -- especially Privacy Policy placeholders -- before publishing.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"ERROR: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
