from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI
import requests
from bs4 import BeautifulSoup


TEXT_CAP = 12000
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"

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


def analyze_brand(
    website_url: str = "",
    facebook_url: str = "",
    pasted_text: str = "",
    ai_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_texts = [pasted_text]
    source_warnings: list[str] = []

    for url in (website_url, facebook_url):
        fetched_text, warning = fetch_public_text(url)
        if fetched_text:
            source_texts.append(fetched_text)
        if warning:
            source_warnings.append(warning)

    profile = analyze_brand_text(" ".join(source_texts), ai_settings=ai_settings)
    profile["source_warnings"] = source_warnings
    return profile


def analyze_brand_text(text: str, ai_settings: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_text = _collapse_whitespace(text)
    if not normalized_text:
        return _blank_profile()

    ai_config = _resolve_ai_config(ai_settings)
    if ai_config["provider"] != "heuristic" and ai_config["api_key"]:
        try:
            return _analyze_brand_text_openai(
                normalized_text,
                api_key=ai_config["api_key"],
                model=ai_config["model"],
                provider=ai_config["provider"],
                base_url=ai_config["base_url"],
            )
        except Exception as exc:
            profile = _analyze_brand_text_heuristic(normalized_text)
            provider_name = "OpenRouter" if ai_config["provider"] == "openrouter" else "OpenAI"
            profile["analysis_warnings"] = [f"{provider_name} brand extraction failed: {exc}"]
            return profile

    return _analyze_brand_text_heuristic(normalized_text)


def _resolve_ai_config(ai_settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = ai_settings or {}
    provider = str(settings.get("provider") or "").strip().lower()
    if provider in {"", "auto"}:
        provider = "openai" if os.getenv("OPENAI_API_KEY") else "heuristic"
    if provider in {"none", "off", "heuristic only"}:
        provider = "heuristic"
    if provider not in {"heuristic", "openai", "openrouter"}:
        provider = "heuristic"

    if provider == "openai":
        api_key = _clean_openai_key(settings.get("api_key") or os.getenv("OPENAI_API_KEY"))
        if _is_placeholder_openai_key(api_key):
            api_key = ""
        return {
            "provider": "openai",
            "api_key": api_key,
            "model": str(settings.get("model") or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL).strip(),
            "base_url": None,
        }

    if provider == "openrouter":
        api_key = _clean_openai_key(settings.get("api_key") or os.getenv("OPENROUTER_API_KEY"))
        if _is_placeholder_openai_key(api_key) or _is_placeholder_openrouter_key(api_key):
            api_key = ""
        return {
            "provider": "openrouter",
            "api_key": api_key,
            "model": str(settings.get("model") or os.getenv("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL).strip(),
            "base_url": OPENROUTER_BASE_URL,
        }

    return {"provider": "heuristic", "api_key": "", "model": "", "base_url": None}


def _analyze_brand_text_openai(
    text: str,
    *,
    api_key: str,
    model: str,
    provider: str,
    base_url: str | None,
) -> dict[str, Any]:
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
        client_kwargs["default_headers"] = {
            "HTTP-Referer": "http://localhost:8501",
            "X-OpenRouter-Title": "Thai TikTok KOL Matcher",
        }
    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract a concise influencer-matching brand profile as JSON only. "
                    "Use snake_case strings. Include Thai market search terms when relevant."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Return JSON with keys: category, keywords, target_audience, tone, locations, "
                    "content_pillars, thai_search_terms, summary. Brand text:\n"
                    f"{text[:TEXT_CAP]}"
                ),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    return _validated_openai_profile(parsed, analysis_mode=provider)


def _validated_openai_profile(parsed: dict[str, Any], analysis_mode: str = "openai") -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI response was not a JSON object")
    category = _string_value(parsed.get("category"), "unknown")
    profile = {
        "category": category,
        "keywords": _string_list(parsed.get("keywords")),
        "target_audience": _string_list(parsed.get("target_audience")),
        "tone": _string_list(parsed.get("tone")) or ["general"],
        "locations": _string_list(parsed.get("locations")),
        "content_pillars": _string_list(parsed.get("content_pillars")),
        "thai_search_terms": _string_list(parsed.get("thai_search_terms")),
        "analysis_mode": analysis_mode,
        "analysis_warnings": [],
        "summary": _string_value(parsed.get("summary"), "Brand text was analyzed with OpenAI."),
    }
    if not profile["content_pillars"]:
        profile["content_pillars"] = _detect_content_pillars(profile["keywords"], profile["tone"], profile["locations"])
    return profile


def _analyze_brand_text_heuristic(normalized_text: str) -> dict[str, Any]:

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
        "thai_search_terms": _thai_search_terms(keywords, locations),
        "analysis_mode": "heuristic",
        "analysis_warnings": [],
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
        "thai_search_terms": [],
        "analysis_mode": "heuristic",
        "analysis_warnings": [],
        "summary": "No usable brand text was provided.",
    }


def _clean_openai_key(value: Any) -> str:
    if value is None:
        return ""
    token = str(value).strip()
    while len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
        token = token[1:-1].strip()
    return token


def _is_placeholder_openai_key(value: str) -> bool:
    return value.lower() in {
        "your-openai-key",
        "paste-your-real-openai-api-key-here",
        "paste-your-real-openai-api-token-here",
    }


def _is_placeholder_openrouter_key(value: str) -> bool:
    return value.lower() in {
        "your-openrouter-key",
        "paste-your-real-openrouter-api-key-here",
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_value(value: Any, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _thai_search_terms(keywords: list[str], locations: list[str]) -> list[str]:
    terms: list[str] = []
    if any(keyword in keywords for keyword in ("cafe", "coffee", "dessert", "brunch")):
        terms.extend(["รีวิวคาเฟ่", "คาเฟ่"])
        if "Bangkok" in locations:
            terms.extend(["คาเฟ่กรุงเทพ", "bangkokcafe", "cafehoppingbkk"])
        if "Ari" in locations:
            terms.extend(["คาเฟ่อารีย์"])
    deduped: list[str] = []
    for term in terms:
        if term not in deduped:
            deduped.append(term)
    return deduped


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
