import requests

import brand_analyzer
from brand_analyzer import analyze_brand, analyze_brand_text, fetch_public_text


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


def test_empty_text_returns_fresh_default_lists():
    first_profile = analyze_brand_text("")
    first_profile["keywords"].append("mutated")

    second_profile = analyze_brand_text("")

    assert second_profile["keywords"] == []


def test_blank_url_returns_empty_text_without_request(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.get should not be called for blank URLs")

    monkeypatch.setattr(requests, "get", fail_if_called)

    assert fetch_public_text("  ") == ("", None)


def test_request_failure_returns_empty_text_and_warning(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(requests, "get", raise_timeout)

    text, warning = fetch_public_text("https://example.com")

    assert text == ""
    assert "Could not fetch https://example.com" in warning
    assert "timed out" in warning


def test_fetch_public_text_cleans_and_caps_html(monkeypatch):
    visible_text = " ".join(["coffee"] * 13000)
    html = f"""
    <html>
      <head>
        <style>.hidden {{ color: red; }}</style>
        <script>console.log("ignore");</script>
        <noscript>ignore this fallback</noscript>
      </head>
      <body>
        <h1>Bangkok Cafe</h1>
        <p>{visible_text}</p>
      </body>
    </html>
    """

    class FakeResponse:
        text = html

        def raise_for_status(self):
            return None

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    text, warning = fetch_public_text("https://example.com")

    assert warning is None
    assert "console.log" not in text
    assert ".hidden" not in text
    assert "ignore this fallback" not in text
    assert "\n" not in text
    assert "  " not in text
    assert text.startswith("Bangkok Cafe coffee")
    assert len(text) == 12000


def test_analyze_brand_combines_sources_and_records_warnings(monkeypatch):
    def fake_fetch_public_text(url):
        if "site" in url:
            return "Bangkok cafe serving coffee", None
        return "", f"Could not fetch {url}: denied"

    monkeypatch.setattr(brand_analyzer, "fetch_public_text", fake_fetch_public_text)

    profile = analyze_brand(
        website_url="https://site.example",
        facebook_url="https://facebook.example",
        pasted_text="Ari dessert spot for students",
    )

    assert profile["category"] == "cafe_restaurant"
    assert "coffee" in profile["keywords"]
    assert "dessert" in profile["keywords"]
    assert "Bangkok" in profile["locations"]
    assert "Ari" in profile["locations"]
    assert "students" in profile["target_audience"]
    assert profile["source_warnings"] == ["Could not fetch https://facebook.example: denied"]
