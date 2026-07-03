from kol_data import load_sample_kols
from matcher import rank_kols


CAFE_PROFILE = {
    "category": "cafe_restaurant",
    "keywords": ["cafe", "coffee", "dessert"],
    "target_audience": ["office_workers", "students", "cafe_hoppers"],
    "tone": ["cozy", "aesthetic"],
    "locations": ["Bangkok"],
    "content_pillars": ["specialty coffee", "dessert reviews", "photogenic cafe content"],
}


def test_ranks_cafe_creator_above_unrelated_creator():
    df = load_sample_kols()
    ranked = rank_kols(CAFE_PROFILE, df)

    top_handles = ranked.head(8)["handle"].tolist()

    assert "@maycafehop" in top_handles
    assert ranked.iloc[0]["match_score"] >= 70
    assert ranked[ranked["handle"] == "@beautywithbow"].iloc[0]["match_score"] < ranked.iloc[0]["match_score"]


def test_score_components_are_in_range():
    df = load_sample_kols()
    ranked = rank_kols(CAFE_PROFILE, df)

    for column in [
        "niche_score",
        "style_score",
        "engagement_score",
        "audience_score",
        "location_score",
        "match_score",
    ]:
        assert ranked[column].between(0, 100).all()

