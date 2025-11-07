import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Euro Club Index Ratings", layout="wide")

st.title("🏆 Euro Club Index – Club Ratings")
st.caption("Live data from euroclubindex.com")

@st.cache_data(ttl=3600)
def fetch_club_ratings():
    url = "https://www.euroclubindex.com/wp-json/happyhorizon/v1/get-module-latest-ranking/?ppp=-1&pagination=1&search="
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    if not items:
        return pd.DataFrame()

    # Flatten nested rankData
    records = []
    for item in items:
        rank_info = item.get("rankData", {})
        record = {
            "Rank": rank_info.get("Rank"),
            "PrevRank": rank_info.get("PrevRank"),
            "Club": rank_info.get("teamName"),
            "Country": rank_info.get("teamNation"),
            "Points": float(rank_info.get("Points", 0)),
            "PrevPoints": float(rank_info.get("PrevPoints", 0)),
            "RankChange": rank_info.get("RankDifference"),
            "PointsChange": rank_info.get("PointsDifference"),
            "Link": item.get("permalink"),
        }
        records.append(record)

    df = pd.DataFrame(records)
    df["Rank"] = pd.to_numeric(df["Rank"], errors="coerce")
    df.sort_values("Rank", inplace=True)
    return df

try:
    df = fetch_club_ratings()
    if df.empty:
        st.warning("No data received from API.")
    else:
        search = st.text_input("Search for a club or country:")
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Error fetching data: {e}")
