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
