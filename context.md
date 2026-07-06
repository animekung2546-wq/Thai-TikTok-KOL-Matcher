# Project Context

## Overview

This repository contains a working prototype for the Convert Cake AI Engineer assessment:
**TikTok KOL Matcher for the Thai market**.

The app helps a marketing team analyze a client's website, Facebook page, or pasted brand text, then ranks Thai TikTok KOLs against that brand profile. The prototype targets a reliable Loom demo rather than fragile live scraping.

## Current Status

- Branch: `master`
- App entrypoint: `app.py`
- Local app URL when running: `http://localhost:8501`
- Test suite: `39 passed` on the last verified run
- The app runs without API keys by using heuristic analysis and bundled sample KOL data.
- API keys can be entered directly in the Streamlit sidebar for the current session.
- Optional environment variables:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL`
  - `APIFY_TOKEN`
  - `APIFY_ACTOR_ID`
  - `APIFY_MAX_ITEMS`
  - `APIFY_INPUT_JSON`

## How To Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## How To Test

```powershell
.venv\Scripts\python.exe -m pytest -v
```

Expected result:

```txt
39 passed
```

## Main Files

- `app.py`: Streamlit UI for the full demo flow.
- `brand_analyzer.py`: Fetches public page text, uses OpenAI/OpenRouter brand extraction when configured, and falls back to heuristics.
- `kol_data.py`: Loads the bundled KOL dataset and provides the optional Apify normalization/filtering boundary.
- `matcher.py`: Scores and ranks KOLs using weighted matching.
- `reporting.py`: Generates CSV and Markdown exports.
- `data/sample_kols.csv`: Bundled Thai KOL sample dataset.
- `README.md`: Setup, run instructions, demo flow, and ethics notes.

## Tests

- `tests/test_brand_analyzer.py`: Brand extraction, OpenAI/OpenRouter provider behavior, fetch fallback, HTML cleanup, source warnings.
- `tests/test_kol_data.py`: CSV schema, sample metadata, Apify fallback warnings, Thai-market filtering, URL normalization.
- `tests/test_matcher.py`: Score ranges and relevant KOL ranking.
- `tests/test_reporting.py`: CSV and Markdown export content.
- `tests/test_smoke_demo.py`: No-key end-to-end demo check with at least five TikTok links.

## Demo Flow

1. Run `streamlit run app.py`.
2. Open `http://localhost:8501`.
3. Click **Load Thai Cafe Demo**.
4. Click **Analyze and Match KOLs**.
5. Review the Brand Profile Summary.
6. Walk through the Top KOL cards.
7. Open the detailed ranking table.
8. Download CSV and Markdown reports.

## Matching Model

The matcher uses weighted scoring:

- Niche/category fit: 30%
- Content style and keyword fit: 25%
- Engagement quality: 20%
- Audience demographic fit: 15%
- Thailand/location fit: 10%

The matcher returns a `match_score`, component scores, and a recommendation reason for each KOL.

## Data Notes

The sample KOL dataset contains 24 rows. Demographic fields use `demographics_source=sample_estimate` so downstream users know these values are prototype metadata, not verified audience data.

AI brand extraction returns category, keywords, audience, tone, locations, content pillars, Thai search terms, and a summary. The Streamlit sidebar supports Heuristic only, OpenAI, and OpenRouter. OpenRouter uses the OpenAI-compatible base URL `https://openrouter.ai/api/v1`, defaults to `openai/gpt-oss-20b:free`, and exposes free-model presets. If OpenRouter returns empty/non-JSON content, the app retries once without JSON mode before falling back to heuristic extraction with a warning.

Apify normalization uses `demographics_source=live_unverified` by default for raw live records. When `APIFY_TOKEN` exists and the sidebar Apify option is enabled, the app calls an Apify Actor and normalizes dataset items into the KOL schema. Live rows must pass both brand relevance and Thai-market signal filters before ranking. If the Actor fails or returns no usable profiles, the app falls back to the sample dataset and shows a warning.

## Ethics and Privacy

- Use public information only.
- Do not bypass login walls, private profiles, or platform access controls.
- Treat sample demographics as estimates.
- Use match scores as decision support, not as an automatic final decision.
- Keep human marketing review in the workflow before outreach.

## Known Constraints

- Facebook scraping is best-effort and can fail because many pages block unauthenticated access.
- TikTok live data depends on the configured Apify Actor, account quota, TikTok availability, and whether Apify returns enough Thai-market signals in public fields.
- `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, and `APIFY_TOKEN` are optional; the no-key demo path still works.

## Useful Docs

- Design spec: `docs/superpowers/specs/2026-07-03-tiktok-kol-matcher-design.md`
- Implementation plan: `docs/superpowers/plans/2026-07-03-tiktok-kol-matcher.md`

