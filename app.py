import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="Euro Club Index Ratings & Odds", layout="wide")

st.title("🏆 Euro Club Index – Ratings & Match Odds")

@st.cache_data(ttl=3600)
def fetch_club_ratings():
    url = "https://www.euroclubindex.com/wp-json/happyhorizon/v1/get-module-latest-ranking/?ppp=-1&pagination=1&search="
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    records = []
    for item in items:
        rank_info = item.get("rankData", {})
        record = {
            "Club": rank_info.get("teamName"),
            "Country": rank_info.get("teamNation"),
            "Points": float(rank_info.get("Points", 0)),
        }
        records.append(record)
    df = pd.DataFrame(records)
    df.dropna(subset=["Club"], inplace=True)
    return df

df = fetch_club_ratings()

tab1, tab2 = st.tabs(["📊 Club Ratings", "⚽ Match Odds Calculator"])

# --- TAB 1 ---
with tab1:
    st.subheader("Full Club Ratings Table")
    search = st.text_input("Search clubs or countries")
    filtered = (
        df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        if search else df
    )
    st.dataframe(filtered.sort_values("Points", ascending=False), use_container_width=True)

# --- TAB 2 ---
with tab2:
    st.subheader("Predict Match Odds from Ratings")

    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Select Home Club", df["Club"].unique())
    with col2:
        away_team = st.selectbox("Select Away Club", df["Club"].unique())

    if home_team and away_team and home_team != away_team:
        home_points = df.loc[df["Club"] == home_team, "Points"].iloc[0]
        away_points = df.loc[df["Club"] == away_team, "Points"].iloc[0]
        diff = home_points - away_points

        # --- Model parameters ---
        k = np.log(2) / 250  # logistic slope
        p_home = 1 / (1 + np.exp(-k * diff))
        p_draw = 0.25 * np.exp(-abs(diff) / 800)
        p_away = max(0, 1 - p_home - p_draw)

        # Normalize to sum 1
        total = p_home + p_draw + p_away
        p_home /= total
        p_draw /= total
        p_away /= total

        odds_home = 1 / p_home
        odds_draw = 1 / p_draw
        odds_away = 1 / p_away

        st.markdown(f"### Rating difference: `{diff:.0f}`")
        st.write(f"Home ECI: {home_points:.1f}, Away ECI: {away_points:.1f}")

        st.metric("Home Win Probability", f"{p_home*100:.1f}%", f"Odds {odds_home:.2f}")
        st.metric("Draw Probability", f"{p_draw*100:.1f}%", f"Odds {odds_draw:.2f}")
        st.metric("Away Win Probability", f"{p_away*100:.1f}%", f"Odds {odds_away:.2f}")

        st.caption("Probabilities derived using logistic ECI-difference model (Δ=500 → 66% home win).")
    else:
        st.info("Select two different clubs to calculate odds.")
