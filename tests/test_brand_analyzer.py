import requests

import brand_analyzer
from brand_analyzer import analyze_brand, analyze_brand_text, fetch_public_text


class FakeOpenAIMessage:
    def __init__(self, content):
        self.content = content


class FakeOpenAIChoice:
    def __init__(self, content):
        self.message = FakeOpenAIMessage(content)


class FakeOpenAIResponse:
    def __init__(self, content):
        self.choices = [FakeOpenAIChoice(content)]


class FakeChatCompletions:
    calls = []
    response_content = "{}"

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeOpenAIResponse(self.response_content)


class FakeChat:
    def __init__(self):
        self.completions = FakeChatCompletions()


class FakeOpenAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.chat = FakeChat()


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


def test_openai_key_uses_ai_brand_extraction(monkeypatch):
    FakeChatCompletions.calls = []
    FakeChatCompletions.response_content = """
    {
      "category": "cafe_restaurant",
      "keywords": ["cafe", "coffee", "dessert"],
      "target_audience": ["office_workers", "cafe_hoppers"],
      "tone": ["cozy", "aesthetic"],
      "locations": ["Bangkok", "Ari"],
      "content_pillars": ["specialty coffee", "desserts and bakery"],
      "thai_search_terms": ["รีวิวคาเฟ่", "คาเฟ่อารีย์", "bangkokcafe"],
      "summary": "Cozy Ari cafe for coffee and dessert content."
    }
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(brand_analyzer, "OpenAI", FakeOpenAIClient)

    profile = analyze_brand_text("Ari cafe with specialty coffee and croissants")

    assert profile["analysis_mode"] == "openai"
    assert profile["keywords"] == ["cafe", "coffee", "dessert"]
    assert profile["thai_search_terms"] == ["รีวิวคาเฟ่", "คาเฟ่อารีย์", "bangkokcafe"]
    assert FakeChatCompletions.calls[0]["response_format"] == {"type": "json_object"}


def test_openai_failure_falls_back_to_heuristic(monkeypatch):
    class FailingChatCompletions:
        def create(self, **kwargs):
            raise RuntimeError("rate limited")

    class FailingChat:
        def __init__(self):
            self.completions = FailingChatCompletions()

    class FailingOpenAIClient:
        def __init__(self, api_key):
            self.chat = FailingChat()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(brand_analyzer, "OpenAI", FailingOpenAIClient)

    profile = analyze_brand_text("Bangkok cafe serving coffee")

    assert profile["analysis_mode"] == "heuristic"
    assert "coffee" in profile["keywords"]
    assert "OpenAI brand extraction failed" in profile["analysis_warnings"][0]


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
