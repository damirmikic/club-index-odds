import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Euro Club Index Ratings", layout="wide")

st.title("🏆 Euro Club Index – Club Ratings")
st.caption("Data fetched live from euroclubindex.com")

@st.cache_data(ttl=3600)
def fetch_club_ratings():
    url = "https://www.euroclubindex.com/wp-json/happyhorizon/v1/get-module-latest-ranking/?ppp=-1&pagination=1&search="
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data

try:
    data = fetch_club_ratings()
    clubs = data.get("data", [])
    df = pd.DataFrame(clubs)

    # Select and rename useful columns if present
    rename_map = {
        "rank": "Rank",
        "club": "Club",
        "country": "Country",
        "points": "Points",
        "league": "League",
    }
    for k, v in rename_map.items():
        if k in df.columns:
            df.rename(columns={k: v}, inplace=True)

    # Search bar
    search = st.text_input("Search for a club or league:")
    if search:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

    # Display
    st.dataframe(df.sort_values("Rank") if "Rank" in df.columns else df, use_container_width=True)

except Exception as e:
    st.error(f"Error fetching data: {e}")
