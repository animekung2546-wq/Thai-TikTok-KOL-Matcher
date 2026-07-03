from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd


DATA_PATH = Path(__file__).parent / "data" / "sample_kols.csv"
DEFAULT_APIFY_ACTOR_ID = "clockworks/free-tiktok-scraper"
DEFAULT_APIFY_MAX_ITEMS = 20
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
    "demographics_source",
    "cost_tier",
    "brand_safety_notes",
]


class ApifyFetchError(RuntimeError):
    pass


def load_sample_kols(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required KOL columns: {', '.join(missing_columns)}")
    for column in ["niche_tags", "style_tags"]:
        df[column] = df[column].fillna("").astype(str)
    df["profile_url"] = df["profile_url"].fillna("")
    df["demographics_source"] = df["demographics_source"].fillna("sample_estimate")
    return df


def load_kols(use_apify: bool = False, brand_profile: dict[str, Any] | None = None) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if not use_apify:
        return load_sample_kols(), warnings

    api_token = _clean_apify_token(os.getenv("APIFY_TOKEN"))
    if not api_token:
        warnings.append("APIFY_TOKEN is missing, so the app is using the bundled sample KOL dataset.")
        return load_sample_kols(), warnings
    if _is_placeholder_apify_token(api_token):
        warnings.append(
            "APIFY_TOKEN still contains the placeholder value. Replace it with a real Apify API token from "
            "Apify Console > Settings > API & Integrations."
        )
        return load_sample_kols(), warnings

    try:
        live_kols = fetch_apify_kols(brand_profile=brand_profile)
    except ApifyFetchError as exc:
        warnings.append(f"Apify live fetch failed: {exc}. Using the bundled sample KOL dataset.")
        return load_sample_kols(), warnings

    if live_kols.empty:
        warnings.append("Apify returned no usable TikTok profiles, so the app is using the bundled sample KOL dataset.")
        return load_sample_kols(), warnings

    warnings.append(f"Loaded {len(live_kols)} live TikTok profiles from Apify.")
    return live_kols, warnings


def fetch_apify_kols(
    brand_profile: dict[str, Any] | None = None,
    *,
    token: str | None = None,
    actor_id: str | None = None,
    max_items: int | None = None,
    client_factory: Any | None = None,
) -> pd.DataFrame:
    api_token = _clean_apify_token(token if token is not None else os.getenv("APIFY_TOKEN"))
    if not api_token:
        raise ApifyFetchError("APIFY_TOKEN is missing")
    if _is_placeholder_apify_token(api_token):
        raise ApifyFetchError(
            "APIFY_TOKEN still contains the placeholder value. Replace it with a real Apify API token."
        )

    actor_name = actor_id or os.getenv("APIFY_ACTOR_ID") or DEFAULT_APIFY_ACTOR_ID
    item_limit = max_items or _env_int("APIFY_MAX_ITEMS", DEFAULT_APIFY_MAX_ITEMS)
    actor_input = build_apify_actor_input(brand_profile or {}, item_limit)

    try:
        if client_factory is None:
            from apify_client import ApifyClient

            client_factory = ApifyClient
        client = client_factory(api_token)
        run = client.actor(actor_name).call(run_input=actor_input)
        dataset_id = _read_field(run, "defaultDatasetId") or _read_field(run, "default_dataset_id")
        if not dataset_id:
            raise ApifyFetchError("Actor run did not return a default dataset ID")
        items_page = client.dataset(dataset_id).list_items(limit=item_limit, clean=True)
        raw_items = _dataset_items(items_page)
    except ApifyFetchError:
        raise
    except Exception as exc:
        error_message = str(exc)
        if "authentication token" in error_message.lower() or "user was not found" in error_message.lower():
            error_message = (
                "Apify rejected APIFY_TOKEN. Copy a valid API token from Apify Console > Settings > "
                "API & Integrations, set APIFY_TOKEN again, then restart Streamlit."
            )
        raise ApifyFetchError(error_message) from exc

    rows = []
    for item in raw_items[:item_limit]:
        row = normalize_apify_profile(item)
        if row["handle"] == "@unknown" or not row["profile_url"].startswith("https://www.tiktok.com/@"):
            continue
        if not _is_brand_relevant_live_item(item, row, brand_profile or {}):
            continue
        rows.append(row)
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def build_apify_actor_input(brand_profile: dict[str, Any], max_items: int) -> dict[str, Any]:
    custom_input = os.getenv("APIFY_INPUT_JSON")
    if custom_input:
        try:
            parsed_input = json.loads(custom_input)
        except json.JSONDecodeError as exc:
            raise ApifyFetchError(f"APIFY_INPUT_JSON is invalid JSON: {exc}") from exc
        if not isinstance(parsed_input, dict):
            raise ApifyFetchError("APIFY_INPUT_JSON must decode to a JSON object")
        return parsed_input

    hashtags = _hashtags_from_brand_profile(brand_profile)
    return {
        "hashtags": hashtags,
        "resultsPerPage": max_items,
        "maxFollowersPerProfile": 0,
        "maxFollowingPerProfile": 0,
        "commentsPerPost": 0,
        "topLevelCommentsPerPost": 0,
        "maxRepliesPerComment": 0,
        "proxyCountryCode": "None",
    }


def _hashtags_from_brand_profile(brand_profile: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ["keywords", "content_pillars"]:
        raw_value = brand_profile.get(key, [])
        if isinstance(raw_value, str):
            values.append(raw_value)
        else:
            values.extend(str(value) for value in raw_value)

    hashtags: list[str] = []
    for value in values:
        hashtag = _search_token(value)
        if hashtag and hashtag not in hashtags:
            hashtags.append(hashtag)

    for expansion in _intent_hashtag_expansions(brand_profile, hashtags):
        if expansion not in hashtags:
            hashtags.append(expansion)
    return (hashtags or ["cafe"])[:8]


def _intent_hashtag_expansions(brand_profile: dict[str, Any], hashtags: list[str]) -> list[str]:
    terms = set(hashtags)
    category = _search_token(brand_profile.get("category", ""))
    if category:
        terms.add(category)
    locations = {_search_token(location) for location in brand_profile.get("locations", [])}
    is_bangkok_brand = bool({"bangkok", "bkk"} & locations)
    cafe_terms = {"cafe", "coffee", "dessert", "bakery", "brunch", "croissant", "specialtycoffee"}
    if terms & cafe_terms or "cafe" in category:
        expansions = []
        if is_bangkok_brand:
            expansions.extend(["bangkokcafe", "bkkcafe", "cafehoppingbkk"])
        expansions.extend(["cafehopping", "cafereview", "คาเฟ่", "รีวิวคาเฟ่"])
        return expansions
    return []


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        return default


def _search_token(value: Any) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def _clean_apify_token(value: Any) -> str:
    if value is None:
        return ""
    token = str(value).strip()
    while len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
        token = token[1:-1].strip()
    return token


def _is_placeholder_apify_token(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"your-apify-token", "your_api_token", "my-apify-token", "my_apify_token"}


def _read_field(value: Any, field_name: str) -> Any:
    if isinstance(value, dict):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _dataset_items(items_page: Any) -> list[dict[str, Any]]:
    if isinstance(items_page, list):
        return items_page
    if isinstance(items_page, dict):
        return list(items_page.get("items", []))
    return list(getattr(items_page, "items", []) or [])


def _is_brand_relevant_live_item(raw: dict[str, Any], row: dict[str, Any], brand_profile: dict[str, Any]) -> bool:
    terms = _brand_relevance_terms(brand_profile)
    if not terms:
        return True

    searchable_values = [
        row.get("name", ""),
        row.get("handle", ""),
        row.get("niche_tags", ""),
        row.get("style_tags", ""),
        raw.get("text", ""),
        raw.get("desc", ""),
        raw.get("description", ""),
        raw.get("caption", ""),
    ]
    author_meta = raw.get("authorMeta") or {}
    author_data = raw.get("author") or {}
    searchable_values.extend(
        [
            author_meta.get("name", ""),
            author_meta.get("nickName", ""),
            author_data.get("name", ""),
            author_data.get("nickName", ""),
        ]
    )
    raw_hashtags = raw.get("hashtags") or raw.get("hashtagsList") or []
    if isinstance(raw_hashtags, list):
        for item in raw_hashtags:
            if isinstance(item, dict):
                searchable_values.append(item.get("name") or item.get("title") or "")
            else:
                searchable_values.append(item)
    elif isinstance(raw_hashtags, str):
        searchable_values.append(raw_hashtags)

    compact_text = _search_token(" ".join(str(value) for value in searchable_values if value))
    return any(term in compact_text for term in terms)


def _brand_relevance_terms(brand_profile: dict[str, Any]) -> set[str]:
    values: list[str] = []
    for key in ["category", "keywords", "content_pillars"]:
        raw_value = brand_profile.get(key, [])
        if isinstance(raw_value, str):
            values.append(raw_value)
        else:
            values.extend(str(value) for value in raw_value)

    terms = {_search_token(value) for value in values}
    terms = {term for term in terms if len(term) >= 3 and term not in {"thai", "bkk", "bangkok"}}
    cafe_terms = {"cafe", "coffee", "dessert", "bakery", "brunch", "croissant", "specialtycoffee"}
    if terms & cafe_terms or "cafe" in terms:
        terms |= {"cafe", "coffee", "คาเฟ่", "croissant", "dessert", "bakery", "brunch"}
    return terms


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
    lower_text = text.lower()
    if lower_text.startswith("www.tiktok.com/") or lower_text.startswith("tiktok.com/"):
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


def _coerce_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    return int(float(text))


def _coerce_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    return float(text)


def _estimated_engagement_rate(raw: dict[str, Any]) -> float:
    if raw.get("engagement_rate") not in (None, ""):
        return _coerce_float(raw.get("engagement_rate"))
    views = _coerce_int(raw.get("playCount") or raw.get("avg_views"))
    if views <= 0:
        return 0.0
    interactions = (
        _coerce_int(raw.get("diggCount") or raw.get("likeCount"))
        + _coerce_int(raw.get("commentCount"))
        + _coerce_int(raw.get("shareCount"))
    )
    return round((interactions / views) * 100, 2)


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
        "niche_tags": raw.get("niche_tags") or _tags_from_apify_item(raw),
        "style_tags": raw.get("style_tags") or "live|apify",
        "location": raw.get("location", "Thailand"),
        "followers": _coerce_int(followers),
        "avg_views": _coerce_int(raw.get("playCount") or raw.get("avg_views")),
        "engagement_rate": _estimated_engagement_rate(raw),
        "audience_age": raw.get("audience_age", "unknown"),
        "audience_gender_skew": raw.get("audience_gender_skew", "unknown"),
        "demographics_source": raw.get("demographics_source") or "live_unverified",
        "cost_tier": raw.get("cost_tier", "unknown"),
        "brand_safety_notes": raw.get("brand_safety_notes", "Live data requires manual review"),
    }


def _tags_from_apify_item(raw: dict[str, Any]) -> str:
    raw_hashtags = raw.get("hashtags") or raw.get("hashtagsList") or []
    if isinstance(raw_hashtags, str):
        tags = [raw_hashtags]
    elif isinstance(raw_hashtags, list):
        tags = []
        for item in raw_hashtags:
            if isinstance(item, dict):
                tags.append(str(item.get("name") or item.get("title") or ""))
            else:
                tags.append(str(item))
    else:
        tags = []
    cleaned = []
    for tag in tags:
        normalized = tag.strip().strip("#").lower()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return "|".join(cleaned[:8])
