import pandas as pd
import pytest

from kol_data import load_kols, load_sample_kols, normalize_apify_profile


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


def test_sample_csv_has_expected_rows_and_required_columns():
    df = load_sample_kols()

    assert len(df) == 24
    assert list(df.columns) == REQUIRED_COLUMNS


def test_load_kols_with_apify_missing_token_warns(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)

    df, warnings = load_kols(use_apify=True)

    assert len(df) == 24
    assert warnings == ["APIFY_TOKEN is missing, so the app is using the bundled sample KOL dataset."]


def test_load_kols_with_apify_token_warns_sample_source(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "token-for-test")

    df, warnings = load_kols(use_apify=True)

    assert len(df) == 24
    assert len(warnings) == 1
    assert "APIFY_TOKEN detected" in warnings[0]
    assert "stable demo source" in warnings[0]


def test_video_url_normalizes_to_creator_profile_url():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"name": "creator"},
            "webVideoUrl": "https://www.tiktok.com/@creator/video/123",
        }
    )

    assert profile["handle"] == "@creator"
    assert profile["profile_url"] == "https://www.tiktok.com/@creator"


def test_video_url_does_not_override_explicit_handle():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"uniqueId": "creator"},
            "webVideoUrl": "https://www.tiktok.com/@other/video/123",
        }
    )

    assert profile["handle"] == "@creator"
    assert profile["profile_url"] == "https://www.tiktok.com/@creator"


def test_handle_derives_from_explicit_profile_url_when_author_handle_missing():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"profileUrl": "https://www.tiktok.com/@baz?lang=en"},
            "webVideoUrl": "https://www.tiktok.com/@other/video/123",
        }
    )

    assert profile["handle"] == "@baz"
    assert profile["profile_url"] == "https://www.tiktok.com/@baz"


def test_non_tiktok_profile_url_falls_back_to_handle_profile():
    profile = normalize_apify_profile(
        {
            "author": {"uniqueId": "creator", "profileUrl": "https://example.com/@creator"},
            "webVideoUrl": "https://example.com/@creator/video/123",
        }
    )

    assert profile["handle"] == "@creator"
    assert profile["profile_url"] == "https://www.tiktok.com/@creator"


def test_normalization_output_has_same_schema_keys_as_sample_row():
    sample_keys = set(load_sample_kols().iloc[0].to_dict())

    profile = normalize_apify_profile(
        {
            "author": {"uniqueId": "creator", "nickName": "Creator"},
            "playCount": 1200,
        }
    )

    assert set(profile) == sample_keys


def test_missing_csv_columns_raises_value_error(tmp_path):
    path = tmp_path / "missing_columns.csv"
    pd.DataFrame({"name": ["Only Name"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required KOL columns: .*handle"):
        load_sample_kols(path)
