# Sigma SEO Agent — Autonomous On-Page + Off-Page Pipeline

This runs **without you opening a chat** — GitHub Actions triggers it on a schedule,
it researches, generates, and publishes to your WordPress site as drafts, and drafts
(not sends) off-page outreach for your review.

## What it actually does (honestly)

| Task | Fully automatic? | Notes |
|---|---|---|
| Find new calculator idea | ✅ Yes | Uses Claude + live web search |
| Generate full page (HTML/CSS/JS/schema/blog/FAQ) | ✅ Yes | Matches your existing design system |
| Publish to WordPress | ✅ Yes, as **draft** | You review & click Publish — flip `PUBLISH_STATUS` to `publish` once you trust it |
| Find off-page link prospects | ✅ Yes | Uses Claude + live web search, real specific prospects |
| Write outreach emails | ✅ Yes | Ready to send, non-spammy |
| **Send outreach emails** | ❌ Not in this version | No tool can place a backlink on someone else's site without a human there approving it. Sending is left to you (or ask me to send drafts through your connected Gmail in a chat, with confirmation) |

## One-time setup

### 1. Create a WordPress Application Password
WP Admin → Users → Profile → scroll to "Application Passwords" → name it `seo-agent` → Add.
Copy the generated password (looks like `xxxx xxxx xxxx xxxx xxxx xxxx`).

> If you don't see this section, your WP version may be older than 5.6, or a security
> plugin is hiding it — check plugins like Wordfence for an "Application Passwords" toggle.

### 2. Find your post type
If your calculator pages are normal WordPress Pages built with a "blank/canvas" template
(common with Elementor, Astra, GeneratePress) that strips the header/footer, use `WP_POST_TYPE=pages`.
If you use a custom post type (e.g. a "Tools" CPT), use that type's REST slug instead.

**Important:** by default WordPress strips `<script>` and other "unsafe" HTML from REST
API content unless the authenticated user has the `unfiltered_html` capability (normal
for Admin role on a single, non-multisite install — which you likely have). If your
generated pages come back with scripts/schema stripped, you may need a plugin like
"Unfiltered HTML" or to publish via `raw` content field.

### 3. Create a GitHub repo for this agent
This can be a small **private** repo separate from wherever your site's files live —
it only needs to reach your WordPress site over the internet via its REST API.

```
git init
git add .
git commit -m "Initial Sigma SEO Agent setup"
git remote add origin <your-new-repo-url>
git push -u origin main
```

### 4. Add secrets
Repo → Settings → Secrets and variables → Actions → New repository secret. Add:
- `ANTHROPIC_API_KEY`
- `WP_URL` (e.g. `https://sigmacalculator.net`)
- `WP_USER`
- `WP_APP_PASSWORD`
- `WP_POST_TYPE` (optional, defaults to `pages`)

### 5. Update `built_calculators.json`
This ships with only the 5 calculators mentioned in our chats. **Before your first run,
add your full existing list** (you mentioned 80+ tools) so the agent never suggests
something you've already built. Fastest way: paste your sitemap or tools list into a
chat with me and I'll regenerate this file for you in one shot.

### 6. Test locally first (recommended)
```
pip install requests
export $(cat .env | xargs)   # after copying config.example.env to .env with real values
python agent_publish.py
python agent_offpage.py
```
Check the draft that lands in WordPress and the file in `outreach_drafts/` before
trusting the schedule.

### 7. Let the schedule run
Once pushed with secrets set, GitHub Actions runs automatically per `.github/workflows/seo-agent.yml`:
- **On-page:** Mondays & Thursdays, 09:00 UTC
- **Off-page:** daily, 10:00 UTC

You can also trigger a run anytime: repo → Actions tab → "Sigma SEO Agent" → "Run workflow".

## Adjusting the pace
Publishing 2x/week keeps quality high and avoids WordPress + Google flagging sudden
mass-content patterns. You can loosen the cron schedule in the workflow file once
you've reviewed a few weeks of drafts and are happy with quality.

## Safety defaults built in
- Pages publish as **draft**, not live, until you change `PUBLISH_STATUS`
- Off-page emails are **never auto-sent**
- The agent never repeats a calculator already in `built_calculators.json`
- Every run is logged in the Actions tab — full visibility into what it did and why

## Next upgrades available on request
- Wire real sending via Gmail API (one-time Google Cloud OAuth setup)
- Add Ahrefs/SEMrush/DataForSEO calls for real backlink gap + competitor data
- Auto-audit existing live pages weekly and open a GitHub issue with fixes
- Slack/Telegram notification when a new draft is ready for review
