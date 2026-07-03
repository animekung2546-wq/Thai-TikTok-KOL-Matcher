# TikTok KOL Matcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reliable Streamlit demo app that analyzes a Thai cafe/restaurant brand and ranks Thai TikTok KOLs with links, scores, explanations, and exports.

**Architecture:** The app is a small Python project with focused modules: `brand_analyzer.py` creates a structured brand profile, `kol_data.py` loads sample KOLs and exposes an optional Apify boundary, `matcher.py` scores and ranks KOLs, `reporting.py` exports results, and `app.py` renders the Streamlit workflow. The prototype runs fully without API keys, while `OPENAI_API_KEY` and `APIFY_TOKEN` enable production-oriented paths.

**Tech Stack:** Python 3.10+, Streamlit, pandas, requests, beautifulsoup4, pytest, optional OpenAI SDK, optional Apify client.

---

## File Structure

- Create `requirements.txt`: runtime and test dependencies.
- Create `README.md`: setup, demo, architecture, API key notes, and ethics.
- Create `app.py`: Streamlit UI.
- Create `brand_analyzer.py`: public text fetch, OpenAI extraction path, heuristic fallback.
- Create `kol_data.py`: sample dataset loader and Apify integration boundary.
- Create `matcher.py`: weighted scoring and recommendation explanations.
- Create `reporting.py`: CSV and Markdown export helpers.
- Create `data/sample_kols.csv`: 24 Thai KOL sample rows.
- Create `tests/test_brand_analyzer.py`: fallback analyzer tests.
- Create `tests/test_matcher.py`: scoring and ranking tests.
- Create `tests/test_reporting.py`: export content tests.
- Create `tests/test_smoke_demo.py`: end-to-end no-key demo smoke test.

---

### Task 1: Project Dependencies and README Skeleton

**Files:**
- Create: `requirements.txt`
- Create: `README.md`

- [ ] **Step 1: Create dependency file**

Write `requirements.txt`:

```txt
streamlit==1.41.1
pandas==2.2.3
requests==2.32.3
beautifulsoup4==4.12.3
pytest==8.3.4
openai==1.59.7
apify-client==1.8.1
```

- [ ] **Step 2: Create README skeleton**

Write `README.md`:

```markdown
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

Create a `.env` file or set environment variables in your shell:

```powershell
$env:OPENAI_API_KEY="your-openai-key"
$env:APIFY_TOKEN="your-apify-token"
```

The app works without these keys. `OPENAI_API_KEY` enables AI brand extraction. `APIFY_TOKEN` is reserved for TikTok/Apify data collection experiments and falls back to sample data if unavailable.

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
```

- [ ] **Step 3: Verify files exist**

Run:

```powershell
Test-Path requirements.txt
Test-Path README.md
```

Expected:

```txt
True
True
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add requirements.txt README.md
git commit -m "chore: add project setup docs"
```

Expected: commit succeeds.

---

### Task 2: Brand Analyzer Fallback

**Files:**
- Create: `brand_analyzer.py`
- Create: `tests/test_brand_analyzer.py`

- [ ] **Step 1: Write failing analyzer tests**

Write `tests/test_brand_analyzer.py`:

```python
from brand_analyzer import analyze_brand_text


def test_cafe_text_returns_structured_profile():
    text = """
    A cozy Bangkok cafe in Ari serving specialty coffee, brunch, croissants,
    cakes, and photogenic desserts for office workers, students, and cafe hoppers.
    """

    profile = analyze_brand_text(text)

    assert profile["category"] == "cafe_restaurant"
    assert "coffee" in profile["keywords"]
    assert "dessert" in profile["keywords"]
    assert "Bangkok" in profile["locations"]
    assert "office_workers" in profile["target_audience"]
    assert profile["analysis_mode"] == "heuristic"


def test_empty_text_returns_safe_defaults():
    profile = analyze_brand_text("")

    assert profile["category"] == "unknown"
    assert profile["keywords"] == []
    assert profile["target_audience"] == []
    assert profile["tone"] == ["general"]
    assert profile["content_pillars"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_brand_analyzer.py -v
```

Expected: FAIL because `brand_analyzer.py` does not exist.

- [ ] **Step 3: Implement fallback analyzer**

Write `brand_analyzer.py`:

```python
from __future__ import annotations

import os
import re
from typing import Any

import requests
from bs4 import BeautifulSoup


CAFE_KEYWORDS = {
    "coffee": ["coffee", "กาแฟ", "espresso", "latte"],
    "dessert": ["dessert", "cake", "croissant", "bakery", "ขนม", "เค้ก"],
    "brunch": ["brunch", "breakfast", "toast", "อาหารเช้า"],
    "restaurant": ["restaurant", "food", "อาหาร", "dining"],
    "cafe": ["cafe", "café", "คาเฟ่"],
}

LOCATION_TERMS = {
    "Bangkok": ["bangkok", "กรุงเทพ", "ari", "อารีย์", "siam", "ทองหล่อ", "thonglor"],
    "Chiang Mai": ["chiang mai", "เชียงใหม่"],
    "Phuket": ["phuket", "ภูเก็ต"],
}

AUDIENCE_TERMS = {
    "office_workers": ["office", "worker", "พนักงาน", "ออฟฟิศ"],
    "students": ["student", "university", "นักเรียน", "นักศึกษา"],
    "families": ["family", "kids", "ครอบครัว"],
    "tourists": ["tourist", "travel", "นักท่องเที่ยว"],
    "cafe_hoppers": ["cafe hopper", "cafe hopping", "คาเฟ่ฮอป"],
}

STYLE_TERMS = {
    "cozy": ["cozy", "อบอุ่น", "homey"],
    "aesthetic": ["aesthetic", "photogenic", "instagrammable", "ถ่ายรูป"],
    "premium": ["premium", "luxury", "พรีเมียม"],
    "affordable": ["affordable", "budget", "ราคาดี"],
    "family_friendly": ["family", "kids", "ครอบครัว"],
}


def fetch_public_text(url: str, timeout: int = 8) -> tuple[str, str | None]:
    if not url.strip():
        return "", None

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 TikTokKOLMatcherPrototype/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return "", f"Could not fetch {url}: {exc}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    return text[:12000], None


def analyze_brand(
    website_url: str = "",
    facebook_url: str = "",
    pasted_text: str = "",
) -> dict[str, Any]:
    fetched_texts: list[str] = []
    warnings: list[str] = []

    for url in [website_url, facebook_url]:
        text, warning = fetch_public_text(url)
        if text:
            fetched_texts.append(text)
        if warning:
            warnings.append(warning)

    combined_text = "\n".join([*fetched_texts, pasted_text]).strip()
    profile = analyze_brand_text(combined_text)
    profile["source_warnings"] = warnings
    return profile


def analyze_brand_text(text: str) -> dict[str, Any]:
    normalized = _normalize(text)
    if not normalized:
        return {
            "category": "unknown",
            "keywords": [],
            "target_audience": [],
            "tone": ["general"],
            "locations": [],
            "content_pillars": [],
            "analysis_mode": "heuristic",
            "summary": "No usable brand text was provided.",
        }

    keywords = _match_terms(normalized, CAFE_KEYWORDS)
    locations = _match_terms(normalized, LOCATION_TERMS)
    audience = _match_terms(normalized, AUDIENCE_TERMS)
    tone = _match_terms(normalized, STYLE_TERMS) or ["general"]
    category = "cafe_restaurant" if {"cafe", "coffee", "dessert", "restaurant"} & set(keywords) else "unknown"
    content_pillars = _content_pillars(keywords, tone)

    return {
        "category": category,
        "keywords": keywords,
        "target_audience": audience,
        "tone": tone,
        "locations": locations,
        "content_pillars": content_pillars,
        "analysis_mode": "heuristic",
        "summary": _summary(category, keywords, audience, locations),
    }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _match_terms(normalized_text: str, term_map: dict[str, list[str]]) -> list[str]:
    matches: list[str] = []
    for label, terms in term_map.items():
        if any(term.lower() in normalized_text for term in terms):
            matches.append(label)
    return matches


def _content_pillars(keywords: list[str], tone: list[str]) -> list[str]:
    pillars: list[str] = []
    if "coffee" in keywords:
        pillars.append("specialty coffee")
    if "dessert" in keywords:
        pillars.append("dessert reviews")
    if "brunch" in keywords:
        pillars.append("brunch experience")
    if "aesthetic" in tone:
        pillars.append("photogenic cafe content")
    return pillars


def _summary(category: str, keywords: list[str], audience: list[str], locations: list[str]) -> str:
    return (
        f"Detected category={category}; keywords={', '.join(keywords) or 'none'}; "
        f"audience={', '.join(audience) or 'general'}; locations={', '.join(locations) or 'unknown'}."
    )
```

- [ ] **Step 4: Run analyzer tests**

Run:

```powershell
pytest tests/test_brand_analyzer.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add brand_analyzer.py tests/test_brand_analyzer.py
git commit -m "feat: add heuristic brand analyzer"
```

Expected: commit succeeds.

---

### Task 3: Sample KOL Dataset and Loader

**Files:**
- Create: `data/sample_kols.csv`
- Create: `kol_data.py`

- [ ] **Step 1: Create sample KOL dataset**

Write `data/sample_kols.csv`:

```csv
name,handle,profile_url,niche_tags,style_tags,location,followers,avg_views,engagement_rate,audience_age,audience_gender_skew,cost_tier,brand_safety_notes
May Cafe Hopping,@maycafehop,https://www.tiktok.com/@maycafehop,"cafe|coffee|dessert|lifestyle","aesthetic|cozy|review",Bangkok,185000,52000,5.8,18-34,female_skew,medium,Generally brand-safe food and cafe reviews
Kin Rai Dee,@kinraidee,https://www.tiktok.com/@kinraidee,"food|restaurant|street_food|dessert","review|casual|value",Bangkok,420000,110000,4.9,18-34,mixed,high,Occasional spicy street food humor
BKK Brunch Club,@bkkbrunchclub,https://www.tiktok.com/@bkkbrunchclub,"brunch|cafe|coffee|restaurant","premium|aesthetic|review",Bangkok,98000,31000,6.4,22-38,female_skew,medium,Polished restaurant content
Ari Eats,@arieats,https://www.tiktok.com/@arieats,"cafe|restaurant|dessert|local","cozy|review|neighborhood",Bangkok,76000,22000,7.1,18-34,mixed,low,Local Bangkok neighborhood focus
Thai Dessert Diary,@thaidessertdiary,https://www.tiktok.com/@thaidessertdiary,"dessert|bakery|cafe|food","aesthetic|sweet|review",Bangkok,132000,43000,6.2,18-30,female_skew,medium,Strong dessert alignment
Coffee Nerd TH,@coffeenerdth,https://www.tiktok.com/@coffeenerdth,"coffee|cafe|specialty_coffee","educational|premium|review",Bangkok,88000,26000,5.5,22-40,mixed,medium,Specialty coffee content
Siam Food Finds,@siamfoodfinds,https://www.tiktok.com/@siamfoodfinds,"food|restaurant|cafe|mall","review|trendy|casual",Bangkok,245000,68000,4.7,18-34,mixed,high,Broad food discovery
Cozy Table TH,@cozytableth,https://www.tiktok.com/@cozytableth,"cafe|brunch|dessert","cozy|aesthetic|lifestyle",Bangkok,54000,18000,7.8,18-32,female_skew,low,Micro KOL with strong fit
Hungry Office BKK,@hungryofficebkk,https://www.tiktok.com/@hungryofficebkk,"food|lunch|cafe|restaurant","office|value|review",Bangkok,117000,36000,5.2,22-38,mixed,medium,Good office worker audience
Nomad Bites TH,@nomadbitesth,https://www.tiktok.com/@nomadbitesth,"travel|food|cafe","tourist|casual|review",Bangkok,156000,41000,4.5,20-36,mixed,medium,Travel-heavy audience
Chiang Mai Cafe Map,@cmcafemap,https://www.tiktok.com/@cmcafemap,"cafe|coffee|dessert|travel","cozy|aesthetic|review",Chiang Mai,93000,27000,6.0,18-34,female_skew,medium,Best for Chiang Mai campaigns
Phuket Food Weekend,@phuketfoodweekend,https://www.tiktok.com/@phuketfoodweekend,"food|restaurant|travel|cafe","tourist|review|casual",Phuket,81000,24000,5.4,20-40,mixed,medium,Best for Phuket campaigns
Beauty With Bow,@beautywithbow,https://www.tiktok.com/@beautywithbow,"beauty|skincare|lifestyle","premium|tutorial|review",Bangkok,310000,82000,4.8,18-34,female_skew,high,Beauty-first creator
Fit Thai Daily,@fitthaidaily,https://www.tiktok.com/@fitthaidaily,"fitness|health|meal_prep","educational|routine|wellness",Bangkok,205000,57000,5.1,18-35,mixed,high,Fitness-first creator
Campus Eats TH,@campuseatsth,https://www.tiktok.com/@campuseatsth,"food|cafe|dessert|student","value|casual|review",Bangkok,67000,21000,7.4,16-24,mixed,low,Strong student audience
Family Food Trip,@familyfoodtrip,https://www.tiktok.com/@familyfoodtrip,"food|restaurant|family|cafe","family_friendly|review|weekend",Bangkok,143000,38000,5.0,25-44,female_skew,medium,Family audience
Minimal Cafe Lens,@minimalcafelens,https://www.tiktok.com/@minimalcafelens,"cafe|coffee|dessert|photography","minimal|aesthetic|cozy",Bangkok,59000,20000,8.1,18-30,female_skew,low,Highly visual cafe content
Night Market Guy,@nightmarketguy,https://www.tiktok.com/@nightmarketguy,"street_food|night_market|food","casual|humor|value",Bangkok,390000,125000,4.3,18-34,mixed,high,Night market focus
Pet Friendly Places,@petfriendlyplaces,https://www.tiktok.com/@petfriendlyplaces,"pet|cafe|lifestyle","family_friendly|cozy|review",Bangkok,73000,19000,6.7,22-40,female_skew,low,Good for pet-friendly venues
Vegan Bangkok Guide,@veganbangkokguide,https://www.tiktok.com/@veganbangkokguide,"vegan|restaurant|cafe|health","educational|review|niche",Bangkok,48000,14000,7.0,20-38,mixed,low,Niche vegan audience
Luxury Plates TH,@luxuryplatesth,https://www.tiktok.com/@luxuryplatesth,"fine_dining|restaurant|luxury","premium|polished|review",Bangkok,122000,33000,4.6,25-44,mixed,high,Premium dining focus
Thai Tea Trails,@thaiteatrails,https://www.tiktok.com/@thaiteatrails,"cafe|tea|dessert|local","cozy|review|aesthetic",Bangkok,64000,17000,6.9,18-34,female_skew,low,Strong beverage content
Budget Bite Bangkok,@budgetbitebkk,https://www.tiktok.com/@budgetbitebkk,"food|restaurant|cafe|value","affordable|casual|review",Bangkok,171000,49000,5.6,18-34,mixed,medium,Value-focused content
Art Space Cafe TH,@artspacecafeth,https://www.tiktok.com/@artspacecafeth,"cafe|art|dessert|lifestyle","aesthetic|creative|cozy",Bangkok,52000,16000,7.6,18-32,female_skew,low,Creative cafe audience
```

- [ ] **Step 2: Implement data loader**

Write `kol_data.py`:

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd


DATA_PATH = Path(__file__).parent / "data" / "sample_kols.csv"


def load_sample_kols(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    for column in ["niche_tags", "style_tags"]:
        df[column] = df[column].fillna("").astype(str)
    df["profile_url"] = df["profile_url"].fillna("")
    return df


def load_kols(use_apify: bool = False) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if use_apify and os.getenv("APIFY_TOKEN"):
        warnings.append(
            "APIFY_TOKEN detected. Prototype keeps sample data as the stable demo source; "
            "replace fetch_apify_kols() with a chosen TikTok Actor for live collection."
        )
    elif use_apify:
        warnings.append("APIFY_TOKEN is missing, so the app is using the bundled sample KOL dataset.")
    return load_sample_kols(), warnings


def normalize_apify_profile(raw: dict[str, Any]) -> dict[str, Any]:
    author = raw.get("authorMeta") or raw.get("author") or {}
    handle = author.get("name") or raw.get("username") or raw.get("handle") or "unknown"
    followers = author.get("fans") or author.get("followers") or raw.get("followers") or 0
    return {
        "name": author.get("nickName") or raw.get("name") or handle,
        "handle": f"@{str(handle).lstrip('@')}",
        "profile_url": raw.get("webVideoUrl") or f"https://www.tiktok.com/@{str(handle).lstrip('@')}",
        "niche_tags": raw.get("niche_tags", ""),
        "style_tags": raw.get("style_tags", ""),
        "location": raw.get("location", "Thailand"),
        "followers": int(followers or 0),
        "avg_views": int(raw.get("playCount") or raw.get("avg_views") or 0),
        "engagement_rate": float(raw.get("engagement_rate") or 0),
        "audience_age": raw.get("audience_age", "unknown"),
        "audience_gender_skew": raw.get("audience_gender_skew", "unknown"),
        "cost_tier": raw.get("cost_tier", "unknown"),
        "brand_safety_notes": raw.get("brand_safety_notes", "Live data requires manual review"),
    }
```

- [ ] **Step 3: Verify loader**

Run:

```powershell
python -c "from kol_data import load_sample_kols; df=load_sample_kols(); print(len(df)); print(df['profile_url'].str.contains('tiktok.com').all())"
```

Expected:

```txt
24
True
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add data/sample_kols.csv kol_data.py
git commit -m "feat: add Thai KOL sample dataset"
```

Expected: commit succeeds.

---

### Task 4: Matching and Ranking

**Files:**
- Create: `matcher.py`
- Create: `tests/test_matcher.py`

- [ ] **Step 1: Write failing matcher tests**

Write `tests/test_matcher.py`:

```python
from kol_data import load_sample_kols
from matcher import rank_kols


CAFE_PROFILE = {
    "category": "cafe_restaurant",
    "keywords": ["cafe", "coffee", "dessert"],
    "target_audience": ["office_workers", "students", "cafe_hoppers"],
    "tone": ["cozy", "aesthetic"],
    "locations": ["Bangkok"],
    "content_pillars": ["specialty coffee", "dessert reviews", "photogenic cafe content"],
}


def test_ranks_cafe_creator_above_unrelated_creator():
    df = load_sample_kols()
    ranked = rank_kols(CAFE_PROFILE, df)

    top_handles = ranked.head(8)["handle"].tolist()

    assert "@maycafehop" in top_handles
    assert ranked.iloc[0]["match_score"] >= 70
    assert ranked[ranked["handle"] == "@beautywithbow"].iloc[0]["match_score"] < ranked.iloc[0]["match_score"]


def test_score_components_are_in_range():
    df = load_sample_kols()
    ranked = rank_kols(CAFE_PROFILE, df)

    for column in [
        "niche_score",
        "style_score",
        "engagement_score",
        "audience_score",
        "location_score",
        "match_score",
    ]:
        assert ranked[column].between(0, 100).all()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_matcher.py -v
```

Expected: FAIL because `matcher.py` does not exist.

- [ ] **Step 3: Implement matcher**

Write `matcher.py`:

```python
from __future__ import annotations

from typing import Any

import pandas as pd


WEIGHTS = {
    "niche_score": 0.30,
    "style_score": 0.25,
    "engagement_score": 0.20,
    "audience_score": 0.15,
    "location_score": 0.10,
}

AUDIENCE_TAG_MAP = {
    "office_workers": {"office", "lunch", "value"},
    "students": {"student", "value", "casual"},
    "families": {"family", "family_friendly"},
    "tourists": {"travel", "tourist"},
    "cafe_hoppers": {"cafe", "aesthetic", "lifestyle"},
}


def rank_kols(brand_profile: dict[str, Any], kols: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in kols.iterrows():
        scored = row.to_dict()
        component_scores = score_kol(brand_profile, scored)
        scored.update(component_scores)
        scored["match_score"] = round(
            sum(component_scores[name] * weight for name, weight in WEIGHTS.items()),
            1,
        )
        scored["recommendation_reason"] = build_reason(brand_profile, scored)
        rows.append(scored)

    ranked = pd.DataFrame(rows).sort_values(
        by=["match_score", "engagement_rate", "followers"],
        ascending=[False, False, False],
    )
    return ranked.reset_index(drop=True)


def score_kol(brand_profile: dict[str, Any], kol: dict[str, Any]) -> dict[str, float]:
    brand_keywords = set(brand_profile.get("keywords", []))
    brand_tone = set(brand_profile.get("tone", []))
    brand_audience = set(brand_profile.get("target_audience", []))
    brand_locations = set(brand_profile.get("locations", []))

    niche_tags = _tag_set(kol.get("niche_tags", ""))
    style_tags = _tag_set(kol.get("style_tags", ""))

    niche_score = _overlap_score(brand_keywords, niche_tags)
    style_score = _overlap_score(brand_tone | brand_keywords, style_tags | niche_tags)
    audience_score = _audience_score(brand_audience, niche_tags | style_tags)
    location_score = 100.0 if not brand_locations or kol.get("location") in brand_locations else 45.0
    engagement_score = _engagement_score(float(kol.get("engagement_rate", 0) or 0), int(kol.get("followers", 0) or 0))

    return {
        "niche_score": niche_score,
        "style_score": style_score,
        "engagement_score": engagement_score,
        "audience_score": audience_score,
        "location_score": location_score,
    }


def build_reason(brand_profile: dict[str, Any], kol: dict[str, Any]) -> str:
    strengths: list[str] = []
    if kol["niche_score"] >= 60:
        strengths.append("strong food/cafe niche overlap")
    if kol["style_score"] >= 60:
        strengths.append("content style matches the brand tone")
    if kol["engagement_score"] >= 70:
        strengths.append("healthy engagement quality")
    if kol["location_score"] >= 90:
        strengths.append(f"audience/location fit for {kol.get('location', 'Thailand')}")
    if not strengths:
        strengths.append("some relevance but requires manual review")

    pillars = ", ".join(brand_profile.get("content_pillars", [])[:2])
    if pillars:
        return f"Recommended for {pillars}: " + "; ".join(strengths) + "."
    return "Recommended because " + "; ".join(strengths) + "."


def _tag_set(value: Any) -> set[str]:
    return {part.strip() for part in str(value).split("|") if part.strip()}


def _overlap_score(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 50.0
    overlap = expected & actual
    return round(min(100.0, 35.0 + (len(overlap) / len(expected)) * 65.0), 1) if overlap else 20.0


def _audience_score(brand_audience: set[str], kol_tags: set[str]) -> float:
    if not brand_audience:
        return 50.0
    mapped: set[str] = set()
    for audience in brand_audience:
        mapped |= AUDIENCE_TAG_MAP.get(audience, set())
    return _overlap_score(mapped, kol_tags)


def _engagement_score(engagement_rate: float, followers: int) -> float:
    base = min(100.0, engagement_rate * 12.0)
    if 20_000 <= followers <= 200_000:
        base += 12.0
    elif followers > 200_000:
        base += 5.0
    return round(max(0.0, min(100.0, base)), 1)
```

- [ ] **Step 4: Run matcher tests**

Run:

```powershell
pytest tests/test_matcher.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add matcher.py tests/test_matcher.py
git commit -m "feat: add KOL matching model"
```

Expected: commit succeeds.

---

### Task 5: Reporting Exports

**Files:**
- Create: `reporting.py`
- Create: `tests/test_reporting.py`

- [ ] **Step 1: Write failing reporting tests**

Write `tests/test_reporting.py`:

```python
from kol_data import load_sample_kols
from matcher import rank_kols
from reporting import rankings_to_csv, rankings_to_markdown


def test_markdown_report_contains_tiktok_links():
    profile = {
        "category": "cafe_restaurant",
        "keywords": ["cafe", "coffee", "dessert"],
        "target_audience": ["cafe_hoppers"],
        "tone": ["aesthetic"],
        "locations": ["Bangkok"],
        "content_pillars": ["specialty coffee"],
    }
    ranked = rank_kols(profile, load_sample_kols())

    markdown = rankings_to_markdown(profile, ranked.head(5))

    assert "TikTok KOL Recommendation Report" in markdown
    assert "https://www.tiktok.com/@" in markdown
    assert "Human Review Notes" in markdown


def test_csv_export_contains_profile_url():
    profile = {
        "category": "cafe_restaurant",
        "keywords": ["cafe"],
        "target_audience": [],
        "tone": [],
        "locations": ["Bangkok"],
        "content_pillars": [],
    }
    ranked = rank_kols(profile, load_sample_kols())

    csv_text = rankings_to_csv(ranked.head(3))

    assert "profile_url" in csv_text
    assert "tiktok.com" in csv_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_reporting.py -v
```

Expected: FAIL because `reporting.py` does not exist.

- [ ] **Step 3: Implement reporting helpers**

Write `reporting.py`:

```python
from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd


EXPORT_COLUMNS = [
    "name",
    "handle",
    "profile_url",
    "match_score",
    "niche_score",
    "style_score",
    "engagement_score",
    "audience_score",
    "location_score",
    "followers",
    "avg_views",
    "engagement_rate",
    "location",
    "cost_tier",
    "recommendation_reason",
    "brand_safety_notes",
]


def rankings_to_csv(ranked: pd.DataFrame) -> str:
    buffer = StringIO()
    columns = [column for column in EXPORT_COLUMNS if column in ranked.columns]
    ranked[columns].to_csv(buffer, index=False)
    return buffer.getvalue()


def rankings_to_markdown(brand_profile: dict[str, Any], ranked: pd.DataFrame) -> str:
    lines: list[str] = [
        "# TikTok KOL Recommendation Report",
        "",
        "## Brand Profile",
        "",
        f"- Category: {brand_profile.get('category', 'unknown')}",
        f"- Keywords: {', '.join(brand_profile.get('keywords', [])) or 'none'}",
        f"- Target audience: {', '.join(brand_profile.get('target_audience', [])) or 'general'}",
        f"- Tone: {', '.join(brand_profile.get('tone', [])) or 'general'}",
        f"- Locations: {', '.join(brand_profile.get('locations', [])) or 'unknown'}",
        "",
        "## Recommended TikTok KOLs",
        "",
    ]

    for index, row in ranked.reset_index(drop=True).iterrows():
        lines.extend(
            [
                f"### {index + 1}. {row['name']} ({row['handle']})",
                "",
                f"- TikTok: {row['profile_url']}",
                f"- Match score: {row['match_score']}",
                f"- Followers: {int(row['followers']):,}",
                f"- Engagement rate: {row['engagement_rate']}%",
                f"- Cost tier: {row['cost_tier']}",
                f"- Why this matches: {row['recommendation_reason']}",
                f"- Brand safety notes: {row['brand_safety_notes']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Human Review Notes",
            "",
            "These rankings are decision support for influencer shortlisting. Audience demographics and cost tiers are prototype estimates and should be verified before outreach.",
        ]
    )
    return "\n".join(lines)
```

- [ ] **Step 4: Run reporting tests**

Run:

```powershell
pytest tests/test_reporting.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add reporting.py tests/test_reporting.py
git commit -m "feat: add recommendation exports"
```

Expected: commit succeeds.

---

### Task 6: Streamlit App

**Files:**
- Create: `app.py`
- Modify: `README.md`

- [ ] **Step 1: Write Streamlit app**

Write `app.py`:

```python
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from brand_analyzer import analyze_brand
from kol_data import load_kols
from matcher import rank_kols
from reporting import rankings_to_csv, rankings_to_markdown


DEMO_TEXT = """
Moonlit Spoon Cafe is a cozy Bangkok cafe in Ari serving specialty coffee,
brunch plates, croissants, cakes, and photogenic desserts. The brand targets
office workers, students, tourists, and cafe hoppers who enjoy aesthetic cafe
content, weekend brunch, and friendly neighborhood service.
"""


st.set_page_config(page_title="Thai TikTok KOL Matcher", page_icon="TH", layout="wide")

st.title("Thai TikTok KOL Matcher")
st.caption("Reliable AI demo prototype for Convert Cake influencer shortlisting")

with st.sidebar:
    st.header("Demo Controls")
    use_apify = st.checkbox("Try Apify hook if token exists", value=False)
    top_n = st.slider("Top KOLs", min_value=3, max_value=10, value=5)
    st.markdown("### Runtime")
    st.write("OpenAI key:", "configured" if os.getenv("OPENAI_API_KEY") else "not configured")
    st.write("Apify token:", "configured" if os.getenv("APIFY_TOKEN") else "not configured")

if "pasted_text" not in st.session_state:
    st.session_state.pasted_text = ""
if "website_url" not in st.session_state:
    st.session_state.website_url = ""
if "facebook_url" not in st.session_state:
    st.session_state.facebook_url = ""

col_a, col_b = st.columns([2, 1])
with col_a:
    st.subheader("Client Input")
with col_b:
    if st.button("Load Thai Cafe Demo", use_container_width=True):
        st.session_state.website_url = ""
        st.session_state.facebook_url = ""
        st.session_state.pasted_text = DEMO_TEXT

website_url = st.text_input("Website URL", key="website_url", placeholder="https://example-cafe.com")
facebook_url = st.text_input("Facebook Page URL", key="facebook_url", placeholder="https://facebook.com/examplecafe")
pasted_text = st.text_area(
    "Paste brand or social content",
    key="pasted_text",
    height=160,
    placeholder="Paste website copy, Facebook About text, menu highlights, or campaign brief.",
)

if st.button("Analyze and Match KOLs", type="primary"):
    if not any([website_url.strip(), facebook_url.strip(), pasted_text.strip()]):
        st.error("Add a URL, paste brand content, or click Load Thai Cafe Demo.")
        st.stop()

    profile = analyze_brand(website_url=website_url, facebook_url=facebook_url, pasted_text=pasted_text)
    kols, kol_warnings = load_kols(use_apify=use_apify)
    ranked = rank_kols(profile, kols)

    st.session_state.profile = profile
    st.session_state.ranked = ranked
    st.session_state.kol_warnings = kol_warnings

if "profile" in st.session_state and "ranked" in st.session_state:
    profile = st.session_state.profile
    ranked = st.session_state.ranked

    for warning in profile.get("source_warnings", []):
        st.warning(warning)
    for warning in st.session_state.get("kol_warnings", []):
        st.info(warning)

    st.subheader("Brand Profile Summary")
    profile_cols = st.columns(5)
    profile_cols[0].metric("Category", profile.get("category", "unknown"))
    profile_cols[1].metric("Mode", profile.get("analysis_mode", "heuristic"))
    profile_cols[2].metric("Keywords", len(profile.get("keywords", [])))
    profile_cols[3].metric("Locations", ", ".join(profile.get("locations", [])) or "unknown")
    profile_cols[4].metric("Audience", len(profile.get("target_audience", [])))

    st.write(profile.get("summary", ""))
    st.write("Content pillars:", ", ".join(profile.get("content_pillars", [])) or "none")

    st.subheader(f"Top {top_n} Recommended TikTok KOLs")
    top = ranked.head(top_n)
    card_cols = st.columns(min(3, top_n))
    for index, row in top.reset_index(drop=True).iterrows():
        with card_cols[index % len(card_cols)]:
            st.markdown(f"### {index + 1}. {row['name']}")
            st.markdown(f"[{row['handle']}]({row['profile_url']})")
            st.metric("Match Score", row["match_score"])
            st.write(f"Followers: {int(row['followers']):,}")
            st.write(f"Engagement: {row['engagement_rate']}%")
            st.write(row["recommendation_reason"])

    st.subheader("Detailed Ranking Table")
    display_columns = [
        "name",
        "handle",
        "profile_url",
        "match_score",
        "niche_score",
        "style_score",
        "engagement_score",
        "audience_score",
        "location_score",
        "followers",
        "avg_views",
        "engagement_rate",
        "location",
        "cost_tier",
        "brand_safety_notes",
    ]
    st.dataframe(ranked[display_columns], use_container_width=True, hide_index=True)

    st.subheader("Export")
    csv_text = rankings_to_csv(ranked)
    markdown_text = rankings_to_markdown(profile, top)
    export_cols = st.columns(2)
    export_cols[0].download_button(
        "Download CSV",
        data=csv_text,
        file_name="tiktok_kol_rankings.csv",
        mime="text/csv",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download Markdown Report",
        data=markdown_text,
        file_name="tiktok_kol_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
else:
    st.info("Load the Thai Cafe Demo or enter client content, then click Analyze and Match KOLs.")
```

- [ ] **Step 2: Update README with app screenshot-free verification**

Append to `README.md`:

```markdown

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
```

- [ ] **Step 3: Run import smoke check**

Run:

```powershell
python -c "import app; print('app import ok')"
```

Expected: no Python traceback. Streamlit may print warnings when imported outside `streamlit run`; `app import ok` should appear.

- [ ] **Step 4: Commit**

Run:

```powershell
git add app.py README.md
git commit -m "feat: add Streamlit demo app"
```

Expected: commit succeeds.

---

### Task 7: End-to-End Smoke Test

**Files:**
- Create: `tests/test_smoke_demo.py`

- [ ] **Step 1: Write smoke test**

Write `tests/test_smoke_demo.py`:

```python
from brand_analyzer import analyze_brand_text
from kol_data import load_sample_kols
from matcher import rank_kols
from reporting import rankings_to_markdown


def test_no_key_demo_returns_five_tiktok_links():
    demo_text = """
    A cozy Bangkok cafe in Ari serving specialty coffee, brunch, croissants,
    cakes, and photogenic desserts for office workers, students, and cafe hoppers.
    """

    profile = analyze_brand_text(demo_text)
    ranked = rank_kols(profile, load_sample_kols())
    report = rankings_to_markdown(profile, ranked.head(5))

    assert len(ranked.head(5)) == 5
    assert ranked.head(5)["profile_url"].str.contains("https://www.tiktok.com/@").all()
    assert report.count("https://www.tiktok.com/@") >= 5
```

- [ ] **Step 2: Run full test suite**

Run:

```powershell
pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

Run:

```powershell
git add tests/test_smoke_demo.py
git commit -m "test: add no-key demo smoke test"
```

Expected: commit succeeds.

---

### Task 8: Final Verification and Demo Readiness

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Install dependencies in a virtual environment**

Run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected: dependencies install without errors.

- [ ] **Step 2: Run all tests**

Run:

```powershell
pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Start the Streamlit app**

Run:

```powershell
streamlit run app.py
```

Expected: Streamlit prints a local URL, usually `http://localhost:8501`.

- [ ] **Step 4: Manually verify the demo flow**

In the browser:

1. Click **Load Thai Cafe Demo**.
2. Click **Analyze and Match KOLs**.
3. Confirm Brand Profile Summary appears.
4. Confirm Top KOL cards contain TikTok links.
5. Confirm the Detailed Ranking Table has score breakdown columns.
6. Confirm CSV and Markdown report download buttons are visible.

Expected: the app produces at least five recommended KOLs without any API keys.

- [ ] **Step 5: Add final demo notes**

Append to `README.md`:

```markdown

## Loom Talking Points

- Problem: influencer shortlisting is slow when teams manually inspect client pages and TikTok profiles.
- Prototype: converts client content into a structured brand profile and ranks KOLs using transparent weighted scoring.
- Reliability: works without API keys, avoids fragile login-wall scraping, and includes optional OpenAI/Apify upgrade paths.
- Business value: reduces first-pass KOL discovery time and gives the marketing team a consistent shortlist with reasons.
- Future enhancements: verified live TikTok collection, campaign performance feedback loop, richer brand safety checks, CRM integration, and human approval workflows.
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add README.md
git commit -m "docs: add demo verification notes"
```

Expected: commit succeeds.

- [ ] **Step 7: Report completion**

Run:

```powershell
git status --short
git log --oneline -5
```

Expected: no uncommitted implementation files, and recent commits show the task sequence.
