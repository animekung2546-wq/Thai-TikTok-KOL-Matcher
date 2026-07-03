from brand_analyzer import analyze_brand_text
from kol_data import load_sample_kols
from matcher import rank_kols
from reporting import rankings_to_markdown


def test_no_key_demo_returns_five_tiktok_links():
    demo_text = """
    A cozy Bangkok cafe in Ari serving specialty coffee, brunch, croissants,
    cakes, and photogenic desserts for office workers, students, and cafe hoppers.
    """

    profile = analyze_brand_text(demo_text)
    ranked = rank_kols(profile, load_sample_kols())
    report = rankings_to_markdown(profile, ranked.head(5))

    assert len(ranked.head(5)) == 5
    assert ranked.head(5)["profile_url"].str.contains("https://www.tiktok.com/@").all()
    assert report.count("https://www.tiktok.com/@") >= 5

