from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup


TEXT_CAP = 12000

KEYWORD_PATTERNS: dict[str, tuple[str, ...]] = {
    "coffee": ("coffee", "espresso", "latte", "cappuccino", "americano"),
    "dessert": ("dessert", "desserts", "cake", "cakes", "croissant", "croissants", "pastry", "pastries"),
    "brunch": ("brunch", "breakfast"),
    "restaurant": ("restaurant", "dining", "food", "meal", "lunch", "dinner"),
    "cafe": ("cafe", "coffee shop"),
}

AUDIENCE_PATTERNS: dict[str, tuple[str, ...]] = {
    "office_workers": ("office workers", "office worker", "professionals", "employees"),
    "students": ("students", "student", "university", "college"),
    "tourists": ("tourists", "tourist", "travelers", "travellers", "visitors"),
    "cafe_hoppers": ("cafe hoppers", "cafe hopper"),
    "families": ("family friendly", "families", "family"),
}

TONE_PATTERNS: dict[str, tuple[str, ...]] = {
    "cozy": ("cozy", "cosy", "warm", "comfortable"),
    "aesthetic": ("aesthetic", "photogenic", "instagrammable", "beautiful"),
    "premium": ("premium", "specialty", "speciality", "luxury", "exclusive"),
    "affordable": ("affordable", "budget", "value", "cheap"),
    "family_friendly": ("family friendly", "kid friendly", "children", "kids"),
}

LOCATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "Bangkok": ("Bangkok",),
    "Ari": ("Ari",),
}

CONTENT_PILLAR_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("specialty coffee", ("coffee",)),
    ("desserts and bakery", ("dessert",)),
    ("brunch and dining", ("brunch", "restaurant", "cafe")),
    ("lifestyle and ambience", ("cozy", "aesthetic")),
    ("local discovery", ("Bangkok", "Ari")),
)


def fetch_public_text(url: str, timeout: int = 8) -> tuple[str, str | None]:
    if not url.strip():
        return "", None

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BrandAnalyzer/1.0)"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return "", f"Could not fetch {url}: {exc}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = _collapse_whitespace(soup.get_text(" "))
    return text[:TEXT_CAP], None


def analyze_brand(website_url: str = "", facebook_url: str = "", pasted_text: str = "") -> dict[str, Any]:
    source_texts = [pasted_text]
    source_warnings: list[str] = []

    for url in (website_url, facebook_url):
        fetched_text, warning = fetch_public_text(url)
        if fetched_text:
            source_texts.append(fetched_text)
        if warning:
            source_warnings.append(warning)

    profile = analyze_brand_text(" ".join(source_texts))
    profile["source_warnings"] = source_warnings
    return profile


def analyze_brand_text(text: str) -> dict[str, Any]:
    normalized_text = _collapse_whitespace(text)
    if not normalized_text:
        return _blank_profile()

    keywords = _match_patterns(normalized_text, KEYWORD_PATTERNS)
    audience = _match_patterns(normalized_text, AUDIENCE_PATTERNS)
    tone = _match_patterns(normalized_text, TONE_PATTERNS) or ["general"]
    locations = _match_patterns(normalized_text, LOCATION_PATTERNS)
    category = _detect_category(keywords)
    content_pillars = _detect_content_pillars(keywords, tone, locations)

    return {
        "category": category,
        "keywords": keywords,
        "target_audience": audience,
        "tone": tone,
        "locations": locations,
        "content_pillars": content_pillars,
        "analysis_mode": "heuristic",
        "summary": _build_summary(category, keywords, audience, locations),
    }


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _blank_profile() -> dict[str, Any]:
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


def _match_patterns(text: str, patterns: dict[str, tuple[str, ...]]) -> list[str]:
    matches: list[str] = []
    for label, terms in patterns.items():
        if any(_contains_term(text, term) for term in terms):
            matches.append(label)
    return matches


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE) is not None


def _detect_category(keywords: list[str]) -> str:
    if any(keyword in keywords for keyword in ("coffee", "cafe", "brunch", "dessert", "restaurant")):
        return "cafe_restaurant"
    return "unknown"


def _detect_content_pillars(keywords: list[str], tone: list[str], locations: list[str]) -> list[str]:
    signals = set(keywords) | set(tone) | set(locations)
    return [
        pillar
        for pillar, required_signals in CONTENT_PILLAR_RULES
        if any(signal in signals for signal in required_signals)
    ]


def _build_summary(category: str, keywords: list[str], audience: list[str], locations: list[str]) -> str:
    if category == "unknown":
        return "Brand text was analyzed with heuristic matching, but no clear category was found."

    parts = [f"Detected a {category.replace('_', ' ')} brand"]
    if keywords:
        parts.append(f"with signals for {', '.join(keywords[:4])}")
    if audience:
        parts.append(f"serving {', '.join(audience[:3])}")
    if locations:
        parts.append(f"in {', '.join(locations)}")
    return " ".join(parts) + "."
