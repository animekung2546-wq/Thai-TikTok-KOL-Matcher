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
    "audience_age",
    "audience_gender_skew",
    "demographics_source",
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
                f"- Audience age: {row.get('audience_age', 'unknown')}",
                f"- Audience gender skew: {row.get('audience_gender_skew', 'unknown')}",
                f"- Demographics source: {row.get('demographics_source', 'unknown')}",
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
            (
                "These rankings are decision support for influencer shortlisting. "
                "Audience demographics and cost tiers are prototype estimates and "
                "should be verified before outreach."
            ),
        ]
    )
    return "\n".join(lines)

