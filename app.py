from __future__ import annotations

import os

import streamlit as st

from brand_analyzer import analyze_brand
from kol_data import load_kols
from matcher import rank_kols
from reporting import rankings_to_csv, rankings_to_markdown


DEMO_TEXT = """
Moonlit Spoon Cafe is a cozy Bangkok cafe in Ari serving specialty coffee,
brunch plates, croissants, cakes, and photogenic desserts. The brand targets
office workers, students, tourists, and cafe hoppers who enjoy aesthetic cafe
content, weekend brunch, and friendly neighborhood service.
"""


st.set_page_config(page_title="Thai TikTok KOL Matcher", page_icon="TH", layout="wide")

st.title("Thai TikTok KOL Matcher")
st.caption("Reliable AI demo prototype for Convert Cake influencer shortlisting")

with st.sidebar:
    st.header("Demo Controls")
    use_apify = st.checkbox("Try Apify hook if token exists", value=False)
    top_n = st.slider("Top KOLs", min_value=3, max_value=10, value=5)
    st.markdown("### Runtime")
    st.write("OpenAI key:", "configured" if os.getenv("OPENAI_API_KEY") else "not configured")
    st.write("Apify token:", "configured" if os.getenv("APIFY_TOKEN") else "not configured")

if "pasted_text" not in st.session_state:
    st.session_state.pasted_text = ""
if "website_url" not in st.session_state:
    st.session_state.website_url = ""
if "facebook_url" not in st.session_state:
    st.session_state.facebook_url = ""

col_a, col_b = st.columns([2, 1])
with col_a:
    st.subheader("Client Input")
with col_b:
    if st.button("Load Thai Cafe Demo", use_container_width=True):
        st.session_state.website_url = ""
        st.session_state.facebook_url = ""
        st.session_state.pasted_text = DEMO_TEXT

website_url = st.text_input("Website URL", key="website_url", placeholder="https://example-cafe.com")
facebook_url = st.text_input("Facebook Page URL", key="facebook_url", placeholder="https://facebook.com/examplecafe")
pasted_text = st.text_area(
    "Paste brand or social content",
    key="pasted_text",
    height=160,
    placeholder="Paste website copy, Facebook About text, menu highlights, or campaign brief.",
)

if st.button("Analyze and Match KOLs", type="primary"):
    if not any([website_url.strip(), facebook_url.strip(), pasted_text.strip()]):
        st.error("Add a URL, paste brand content, or click Load Thai Cafe Demo.")
        st.stop()

    profile = analyze_brand(website_url=website_url, facebook_url=facebook_url, pasted_text=pasted_text)
    kols, kol_warnings = load_kols(use_apify=use_apify, brand_profile=profile)
    ranked = rank_kols(profile, kols)

    st.session_state.profile = profile
    st.session_state.ranked = ranked
    st.session_state.kol_warnings = kol_warnings

if "profile" in st.session_state and "ranked" in st.session_state:
    profile = st.session_state.profile
    ranked = st.session_state.ranked

    for warning in profile.get("source_warnings", []):
        st.warning(warning)
    for warning in profile.get("analysis_warnings", []):
        st.warning(warning)
    for warning in st.session_state.get("kol_warnings", []):
        st.info(warning)

    st.subheader("Brand Profile Summary")
    profile_cols = st.columns(5)
    profile_cols[0].metric("Category", profile.get("category", "unknown"))
    profile_cols[1].metric("Mode", profile.get("analysis_mode", "heuristic"))
    profile_cols[2].metric("Keywords", len(profile.get("keywords", [])))
    profile_cols[3].metric("Locations", ", ".join(profile.get("locations", [])) or "unknown")
    profile_cols[4].metric("Audience", len(profile.get("target_audience", [])))

    st.write(profile.get("summary", ""))
    st.write("Content pillars:", ", ".join(profile.get("content_pillars", [])) or "none")

    st.subheader(f"Top {top_n} Recommended TikTok KOLs")
    top = ranked.head(top_n)
    card_cols = st.columns(min(3, top_n))
    for index, row in top.reset_index(drop=True).iterrows():
        with card_cols[index % len(card_cols)]:
            st.markdown(f"### {index + 1}. {row['name']}")
            st.markdown(f"[{row['handle']}]({row['profile_url']})")
            st.metric("Match Score", row["match_score"])
            st.write(f"Followers: {int(row['followers']):,}")
            st.write(f"Engagement: {row['engagement_rate']}%")
            st.write(row["recommendation_reason"])

    st.subheader("Detailed Ranking Table")
    display_columns = [
        "name",
        "handle",
        "profile_url",
        "match_score",
        "niche_score",
        "style_score",
        "engagement_score",
        "audience_score",
        "location_score",
        "followers",
        "avg_views",
        "engagement_rate",
        "location",
        "audience_age",
        "audience_gender_skew",
        "demographics_source",
        "cost_tier",
        "brand_safety_notes",
    ]
    st.dataframe(ranked[display_columns], use_container_width=True, hide_index=True)

    st.subheader("Export")
    csv_text = rankings_to_csv(ranked)
    markdown_text = rankings_to_markdown(profile, top)
    export_cols = st.columns(2)
    export_cols[0].download_button(
        "Download CSV",
        data=csv_text,
        file_name="tiktok_kol_rankings.csv",
        mime="text/csv",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download Markdown Report",
        data=markdown_text,
        file_name="tiktok_kol_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
else:
    st.info("Load the Thai Cafe Demo or enter client content, then click Analyze and Match KOLs.")

