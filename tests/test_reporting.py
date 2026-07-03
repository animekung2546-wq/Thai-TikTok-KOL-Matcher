from kol_data import load_sample_kols
from matcher import rank_kols
from reporting import rankings_to_csv, rankings_to_markdown


def test_markdown_report_contains_tiktok_links():
    profile = {
        "category": "cafe_restaurant",
        "keywords": ["cafe", "coffee", "dessert"],
        "target_audience": ["cafe_hoppers"],
        "tone": ["aesthetic"],
        "locations": ["Bangkok"],
        "content_pillars": ["specialty coffee"],
    }
    ranked = rank_kols(profile, load_sample_kols())

    markdown = rankings_to_markdown(profile, ranked.head(5))

    assert "TikTok KOL Recommendation Report" in markdown
    assert "https://www.tiktok.com/@" in markdown
    assert "Human Review Notes" in markdown


def test_csv_export_contains_profile_url():
    profile = {
        "category": "cafe_restaurant",
        "keywords": ["cafe"],
        "target_audience": [],
        "tone": [],
        "locations": ["Bangkok"],
        "content_pillars": [],
    }
    ranked = rank_kols(profile, load_sample_kols())

    csv_text = rankings_to_csv(ranked.head(3))

    assert "profile_url" in csv_text
    assert "tiktok.com" in csv_text

