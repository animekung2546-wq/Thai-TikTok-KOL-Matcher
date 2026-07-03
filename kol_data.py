from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd


DATA_PATH = Path(__file__).parent / "data" / "sample_kols.csv"
REQUIRED_COLUMNS = [
    "name",
    "handle",
    "profile_url",
    "niche_tags",
    "style_tags",
    "location",
    "followers",
    "avg_views",
    "engagement_rate",
    "audience_age",
    "audience_gender_skew",
    "cost_tier",
    "brand_safety_notes",
]


def load_sample_kols(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required KOL columns: {', '.join(missing_columns)}")
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


def _normalize_tiktok_profile_url(url: Any) -> str:
    handle = _extract_tiktok_handle_from_url(url)
    if not handle:
        return ""
    return f"https://www.tiktok.com/@{handle}"


def _extract_tiktok_handle_from_url(url: Any) -> str:
    if not url:
        return ""
    text = str(url).strip()
    if not text:
        return ""
    if text.startswith("www.tiktok.com/") or text.startswith("tiktok.com/"):
        text = f"https://{text}"

    parsed = urlsplit(text)
    host = parsed.netloc.lower()
    if host not in {"tiktok.com", "www.tiktok.com"} and not host.endswith(".tiktok.com"):
        return ""

    path_parts = [part for part in parsed.path.split("/") if part]
    handle_part = next((part for part in path_parts if part.startswith("@")), "")
    if not handle_part:
        return ""
    return _clean_handle(handle_part)


def _clean_handle(value: Any) -> str:
    if value is None:
        return ""
    handle = str(value).strip().lstrip("@")
    if not handle or handle.lower() == "unknown":
        return ""
    return handle


def _first_handle(*values: Any) -> str:
    for value in values:
        handle = _clean_handle(value)
        if handle:
            return handle
    return ""


def normalize_apify_profile(raw: dict[str, Any]) -> dict[str, Any]:
    author_meta = raw.get("authorMeta") or {}
    author_data = raw.get("author") or {}
    author = author_meta or author_data
    followers = author.get("fans") or author.get("followers") or raw.get("followers") or 0
    explicit_profile_url = (
        _normalize_tiktok_profile_url(author_meta.get("profileUrl"))
        or _normalize_tiktok_profile_url(author_meta.get("profile_url"))
        or _normalize_tiktok_profile_url(author_data.get("profileUrl"))
        or _normalize_tiktok_profile_url(author_data.get("profile_url"))
        or _normalize_tiktok_profile_url(raw.get("profileUrl"))
        or _normalize_tiktok_profile_url(raw.get("profile_url"))
    )
    normalized_handle = (
        _first_handle(
            author_meta.get("name"),
            author_meta.get("uniqueId"),
            author_data.get("name"),
            author_data.get("uniqueId"),
            raw.get("username"),
            raw.get("uniqueId"),
            raw.get("handle"),
        )
        or _extract_tiktok_handle_from_url(explicit_profile_url)
        or _extract_tiktok_handle_from_url(raw.get("webVideoUrl"))
        or "unknown"
    )
    profile_url = explicit_profile_url or f"https://www.tiktok.com/@{normalized_handle}"
    return {
        "name": author.get("nickName") or raw.get("name") or normalized_handle,
        "handle": f"@{normalized_handle}",
        "profile_url": profile_url,
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
