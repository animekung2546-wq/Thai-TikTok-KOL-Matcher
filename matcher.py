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

