import pandas as pd
import pytest

from kol_data import build_apify_actor_input, fetch_apify_kols, load_kols, load_sample_kols, normalize_apify_profile


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


def test_sample_csv_has_expected_rows_and_required_columns():
    df = load_sample_kols()

    assert len(df) == 24
    assert list(df.columns) == REQUIRED_COLUMNS
    assert set(df["demographics_source"]) == {"sample_estimate"}


def test_load_kols_with_apify_missing_token_warns(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)

    df, warnings = load_kols(use_apify=True)

    assert len(df) == 24
    assert warnings == ["APIFY_TOKEN is missing, so the app is using the bundled sample KOL dataset."]


class FakeItemsPage:
    def __init__(self, items):
        self.items = items


class FakeDatasetClient:
    def __init__(self, calls, items):
        self.calls = calls
        self.items = items

    def list_items(self, **kwargs):
        self.calls["list_items"] = kwargs
        return FakeItemsPage(self.items)


class FakeActorClient:
    def __init__(self, calls):
        self.calls = calls

    def call(self, **kwargs):
        self.calls["call"] = kwargs
        return {"defaultDatasetId": "dataset-1"}


class FakeApifyClient:
    calls = {}
    items = []

    def __init__(self, token):
        self.calls["token"] = token

    def actor(self, actor_id):
        self.calls["actor_id"] = actor_id
        return FakeActorClient(self.calls)

    def dataset(self, dataset_id):
        self.calls["dataset_id"] = dataset_id
        return FakeDatasetClient(self.calls, self.items)


def test_build_apify_actor_input_uses_brand_hashtags():
    actor_input = build_apify_actor_input(
        {
            "keywords": ["cafe", "coffee", "dessert"],
            "locations": ["Bangkok"],
            "content_pillars": ["specialty coffee"],
        },
        max_items=12,
    )

    assert "bangkok" not in actor_input["hashtags"]
    assert actor_input["hashtags"][:3] == ["cafe", "coffee", "dessert"]
    assert {"bangkokcafe", "cafehoppingbkk"} <= set(actor_input["hashtags"])
    assert actor_input["resultsPerPage"] == 12
    assert actor_input["commentsPerPost"] == 0


def test_fetch_apify_kols_calls_actor_and_normalizes_items(monkeypatch):
    FakeApifyClient.calls = {}
    FakeApifyClient.items = [
        {
            "authorMeta": {"name": "livecafe", "nickName": "Live Cafe", "fans": "12,345"},
            "webVideoUrl": "https://www.tiktok.com/@livecafe/video/123",
            "playCount": "4,321",
            "hashtags": [{"name": "cafe"}, {"name": "coffee"}, {"name": "bangkokcafe"}],
        }
    ]
    monkeypatch.delenv("APIFY_INPUT_JSON", raising=False)
    monkeypatch.delenv("APIFY_ACTOR_ID", raising=False)

    df = fetch_apify_kols(
        {"keywords": ["cafe", "coffee"], "locations": ["Bangkok"]},
        token="token-for-test",
        max_items=5,
        client_factory=FakeApifyClient,
    )

    assert len(df) == 1
    assert df.iloc[0]["handle"] == "@livecafe"
    assert df.iloc[0]["profile_url"] == "https://www.tiktok.com/@livecafe"
    assert df.iloc[0]["niche_tags"] == "cafe|coffee|bangkokcafe"
    assert df.iloc[0]["followers"] == 12345
    assert FakeApifyClient.calls["token"] == "token-for-test"
    assert FakeApifyClient.calls["actor_id"] == "clockworks/free-tiktok-scraper"
    assert FakeApifyClient.calls["dataset_id"] == "dataset-1"
    assert FakeApifyClient.calls["call"]["run_input"]["hashtags"][:2] == ["cafe", "coffee"]
    assert "bangkok" not in FakeApifyClient.calls["call"]["run_input"]["hashtags"]
    assert FakeApifyClient.calls["list_items"]["limit"] == 5


def test_fetch_apify_kols_filters_live_profiles_without_brand_relevance(monkeypatch):
    FakeApifyClient.calls = {}
    FakeApifyClient.items = [
        {
            "authorMeta": {"name": "bangkokrooftops", "nickName": "Bangkok Rooftops", "fans": 135500},
            "webVideoUrl": "https://www.tiktok.com/@bangkokrooftops/video/123",
            "hashtags": [{"name": "travel"}, {"name": "rooftop"}],
            "text": "Best skyline bars in Bangkok",
        },
        {
            "authorMeta": {"name": "mrmassagez", "nickName": "Black Massage", "fans": 96600},
            "webVideoUrl": "https://www.tiktok.com/@mr.massagez/video/123",
            "hashtags": [{"name": "massage"}, {"name": "wellness"}],
            "text": "Massage review",
        },
        {
            "authorMeta": {"name": "cafebkk", "nickName": "Cafe BKK", "fans": 45000},
            "webVideoUrl": "https://www.tiktok.com/@cafebkk/video/123",
            "hashtags": [{"name": "cafe"}, {"name": "coffee"}],
            "text": "Ari specialty coffee and croissant review",
        },
    ]
    monkeypatch.delenv("APIFY_INPUT_JSON", raising=False)

    df = fetch_apify_kols({"keywords": ["cafe", "coffee"], "content_pillars": ["desserts and bakery"]}, token="token-for-test", client_factory=FakeApifyClient)

    assert df["handle"].tolist() == ["@cafebkk"]


def test_fetch_apify_kols_filters_foreign_profiles_without_thai_market_signal(monkeypatch):
    FakeApifyClient.calls = {}
    FakeApifyClient.items = [
        {
            "authorMeta": {"name": "seoulcafes", "nickName": "Seoul Cafes", "fans": 80000},
            "webVideoUrl": "https://www.tiktok.com/@seoulcafes/video/123",
            "hashtags": [{"name": "cafe"}, {"name": "coffee"}],
            "text": "Best cafe in Seoul for specialty coffee",
        },
        {
            "authorMeta": {"name": "thaicafereview", "nickName": "Thai Cafe Review", "fans": 50000},
            "webVideoUrl": "https://www.tiktok.com/@thaicafereview/video/123",
            "hashtags": [{"name": "cafe"}, {"name": "bangkokcafe"}],
            "text": "รีวิวคาเฟ่กรุงเทพ specialty coffee",
        },
    ]
    monkeypatch.delenv("APIFY_INPUT_JSON", raising=False)

    df = fetch_apify_kols(
        {"keywords": ["cafe", "coffee"], "locations": ["Bangkok"], "thai_search_terms": ["รีวิวคาเฟ่"]},
        token="token-for-test",
        client_factory=FakeApifyClient,
    )

    assert df["handle"].tolist() == ["@thaicafereview"]
    assert df.iloc[0]["location"] == "Thailand"


def test_fetch_apify_kols_strips_accidental_token_quotes(monkeypatch):
    FakeApifyClient.calls = {}
    FakeApifyClient.items = [{"authorMeta": {"name": "cafeth", "nickName": "Cafe TH"}}]
    monkeypatch.delenv("APIFY_INPUT_JSON", raising=False)

    fetch_apify_kols(token=' "token-for-test" ', client_factory=FakeApifyClient)

    assert FakeApifyClient.calls["token"] == "token-for-test"


def test_load_kols_with_apify_token_uses_live_fetch(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "token-for-test")
    monkeypatch.setattr("kol_data.fetch_apify_kols", lambda brand_profile=None, token=None: load_sample_kols().head(2))

    df, warnings = load_kols(use_apify=True, brand_profile={"keywords": ["cafe"]})

    assert len(df) == 2
    assert warnings == ["Loaded 2 live TikTok profiles from Apify."]


def test_load_kols_uses_apify_token_from_app_input(monkeypatch):
    calls = {}

    def fake_fetch(brand_profile=None, token=None):
        calls["token"] = token
        return load_sample_kols().head(1)

    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.setattr("kol_data.fetch_apify_kols", fake_fetch)

    df, warnings = load_kols(use_apify=True, brand_profile={"keywords": ["cafe"]}, apify_token="token-from-app")

    assert len(df) == 1
    assert calls["token"] == "token-from-app"
    assert warnings == ["Loaded 1 live TikTok profiles from Apify."]


def test_load_kols_passes_apify_max_items(monkeypatch):
    calls = {}

    def fake_fetch(brand_profile=None, token=None, max_items=None):
        calls["max_items"] = max_items
        return load_sample_kols().head(3)

    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.setattr("kol_data.fetch_apify_kols", fake_fetch)

    df, warnings = load_kols(
        use_apify=True,
        brand_profile={"keywords": ["cafe"]},
        apify_token="token-from-app",
        apify_max_items=80,
    )

    assert len(df) == 3
    assert calls["max_items"] == 80
    assert warnings == ["Loaded 3 live TikTok profiles from Apify."]


def test_load_kols_with_placeholder_apify_token_warns(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "your-apify-token")

    df, warnings = load_kols(use_apify=True, brand_profile={"keywords": ["cafe"]})

    assert len(df) == 24
    assert "APIFY_TOKEN still contains the placeholder value" in warnings[0]


def test_load_kols_falls_back_when_apify_returns_empty(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "token-for-test")
    monkeypatch.setattr("kol_data.fetch_apify_kols", lambda brand_profile=None, token=None: load_sample_kols().head(0))

    df, warnings = load_kols(use_apify=True, brand_profile={"keywords": ["cafe"]})

    assert len(df) == 24
    assert "Apify returned no usable TikTok profiles" in warnings[0]


def test_video_url_normalizes_to_creator_profile_url():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"name": "creator"},
            "webVideoUrl": "https://www.tiktok.com/@creator/video/123",
        }
    )

    assert profile["handle"] == "@creator"
    assert profile["profile_url"] == "https://www.tiktok.com/@creator"
    assert profile["demographics_source"] == "live_unverified"


def test_normalization_does_not_default_live_location_to_thailand_without_signal():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"name": "seoulcafes"},
            "webVideoUrl": "https://www.tiktok.com/@seoulcafes/video/123",
            "hashtags": [{"name": "cafe"}],
            "text": "Best cafe in Seoul",
        }
    )

    assert profile["location"] == "unknown"


def test_normalization_estimates_engagement_rate_from_live_counts():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"name": "creator"},
            "webVideoUrl": "https://www.tiktok.com/@creator/video/123",
            "playCount": 10000,
            "diggCount": 700,
            "commentCount": 80,
            "shareCount": 20,
        }
    )

    assert profile["avg_views"] == 10000
    assert profile["engagement_rate"] == 8.0


def test_video_url_does_not_override_explicit_handle():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"uniqueId": "creator"},
            "webVideoUrl": "https://www.tiktok.com/@other/video/123",
        }
    )

    assert profile["handle"] == "@creator"
    assert profile["profile_url"] == "https://www.tiktok.com/@creator"


def test_profile_url_normalizes_mixed_case_tiktok_host():
    profile = normalize_apify_profile(
        {
            "profileUrl": "TikTok.com/@creator?lang=en",
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


def test_normalization_coerces_numeric_strings_and_preserves_demographics_source():
    profile = normalize_apify_profile(
        {
            "authorMeta": {"uniqueId": "creator", "fans": "1,234"},
            "playCount": "5,678",
            "engagement_rate": "5.6",
            "demographics_source": "manual_estimate",
        }
    )

    assert profile["followers"] == 1234
    assert profile["avg_views"] == 5678
    assert profile["engagement_rate"] == 5.6
    assert profile["demographics_source"] == "manual_estimate"


def test_missing_csv_columns_raises_value_error(tmp_path):
    path = tmp_path / "missing_columns.csv"
    pd.DataFrame({"name": ["Only Name"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required KOL columns: .*handle"):
        load_sample_kols(path)
