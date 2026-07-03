from brand_analyzer import analyze_brand_text


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
