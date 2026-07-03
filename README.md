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

Set environment variables in your shell:

```powershell
$env:OPENAI_API_KEY="your-openai-key"
$env:APIFY_TOKEN="your-apify-token"
```

The app works without these keys. `OPENAI_API_KEY` enables AI brand extraction. `APIFY_TOKEN` is reserved for TikTok/Apify data collection experiments and falls back to sample data if unavailable.

Keep real API keys local and do not commit them to git.

## Demo Flow for Loom

1. Run `streamlit run app.py`.
2. Click **Load Thai Cafe Demo**.
3. Click **Analyze and Match KOLs**.
4. Review the Brand Profile Summary.
5. Walk through Top 5 KOL cards and the detailed ranking table.
6. Download CSV and Markdown reports.
7. Explain that the app is stable without keys and can be upgraded with OpenAI/Apify hooks.

## Ethics and Privacy

- Uses public information only.
- Does not bypass login walls, private profiles, or platform access controls.
- Sample demographics are estimates for prototype demonstration.
- Final KOL selection should include human marketing review.
- Match scores support decision-making; they should not be treated as the only authority.
