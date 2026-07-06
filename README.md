# TikTok KOL Matcher for Thai Market

AI-powered prototype for matching Thai businesses with relevant TikTok KOLs. Built for Convert Cake's AI Engineer assessment.

## What It Does

- Analyzes a client's website, Facebook URL, or pasted brand content.
- Extracts a brand profile: category, audience, tone, keywords, location, and content pillars.
- Ranks Thai TikTok KOLs by niche fit, content style fit, engagement quality, audience fit, and location fit.
- Shows Top KOL cards, detailed score table, CSV export, and Markdown report export.
- Runs without API keys using deterministic fallback logic and a sample KOL dataset.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
streamlit run app.py
```

## Optional API Keys

You can paste API keys directly in the app sidebar under **API Settings**. Keys are kept in the current Streamlit session and are not written to files.

Supported AI providers:

- **Heuristic only**: no AI API call.
- **OpenAI**: uses `OPENAI_API_KEY` or the OpenAI key pasted in the app.
- **OpenRouter**: uses `OPENROUTER_API_KEY` or the OpenRouter key pasted in the app, with OpenRouter's OpenAI-compatible endpoint.

You can also set environment variables in your shell:

```powershell
$env:OPENAI_API_KEY="paste-your-real-openai-api-key-here"
$env:OPENROUTER_API_KEY="paste-your-real-openrouter-api-key-here"
$env:APIFY_TOKEN="paste-your-real-apify-api-token-here"
```

The app works without these keys. `OPENAI_API_KEY` or `OPENROUTER_API_KEY` enables AI brand-profile extraction with heuristic fallback. `APIFY_TOKEN` enables live TikTok collection through Apify. Live Apify profiles are filtered for brand relevance and Thai-market signals before ranking. If Apify fails or returns no usable profiles, the app falls back to sample data.

Optional model overrides:

```powershell
$env:OPENAI_MODEL="gpt-4o-mini"
$env:OPENROUTER_MODEL="openai/gpt-oss-20b:free"
```

Recommended free OpenRouter models for JSON brand extraction:

- `openai/gpt-oss-20b:free`
- `qwen/qwen3-next-80b-a3b-instruct:free`
- `google/gemma-4-26b-a4b-it:free`
- `nvidia/nemotron-3-super-120b-a12b:free`
- `nvidia/nemotron-nano-9b-v2:free`

If an OpenRouter model returns empty or non-JSON content, the app retries once without JSON mode and then falls back to heuristic extraction with a readable warning.

Run with live Apify collection:

```powershell
$env:APIFY_TOKEN="paste-your-real-apify-api-token-here"
$env:APIFY_MAX_ITEMS="20"
streamlit run app.py
```

Optional Apify controls:

```powershell
$env:APIFY_ACTOR_ID="clockworks/free-tiktok-scraper"
$env:APIFY_MAX_ITEMS="20"
```

The default Actor input is generated from the detected brand keywords and locations. To override it completely, set `APIFY_INPUT_JSON` to a JSON object accepted by the chosen Apify Actor.

Keep real API keys local and do not commit them to git.

To verify the Apify token before running Streamlit:

```powershell
Invoke-RestMethod -Headers @{ Authorization = "Bearer $env:APIFY_TOKEN" } -Uri "https://api.apify.com/v2/users/me"
```

If Apify returns `User was not found or authentication token is not valid`, create or copy a fresh token from Apify Console > Settings > API & Integrations, set `APIFY_TOKEN` again in the same terminal, and restart Streamlit.

## Demo Flow for Loom

1. Run `streamlit run app.py`.
2. Click **Load Thai Cafe Demo**.
3. Click **Analyze and Match KOLs**.
4. Review the Brand Profile Summary.
5. Walk through Top 5 KOL cards and the detailed ranking table.
6. Download CSV and Markdown reports.
7. Explain that the app runs without keys, can accept OpenAI/OpenRouter/Apify keys in the sidebar, and can pull live Thai-market TikTok profiles through Apify.

## Ethics and Privacy

- Uses public information only.
- Does not bypass login walls, private profiles, or platform access controls.
- Sample demographics are estimates for prototype demonstration.
- Final KOL selection should include human marketing review.
- Match scores support decision-making; they should not be treated as the only authority.

## Local Verification

```powershell
pytest -v
streamlit run app.py
```

Expected app behavior:

- The Thai Cafe Demo loads sample brand text.
- Analyze and Match KOLs returns at least five TikTok profiles.
- The detailed table includes score breakdown columns.
- CSV and Markdown downloads are available.

## Loom Talking Points

- Problem: influencer shortlisting is slow when teams manually inspect client pages and TikTok profiles.
- Prototype: converts client content into a structured brand profile and ranks KOLs using transparent weighted scoring.
- Reliability: works without API keys, avoids fragile login-wall scraping, supports OpenAI/OpenRouter brand extraction, and uses Apify live collection when an Apify token is configured.
- Business value: reduces first-pass KOL discovery time and gives the marketing team a consistent shortlist with reasons.
- Future enhancements: verified live TikTok collection, campaign performance feedback loop, richer brand safety checks, CRM integration, and human approval workflows.
