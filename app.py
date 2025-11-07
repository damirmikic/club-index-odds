import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="Euro Club Index Ratings & Odds", layout="wide")

st.title("🏆 Euro Club Index – Ratings & Match Odds")

# ------------------ Fetch Data ------------------
@st.cache_data(ttl=3600)
def fetch_club_ratings():
    url = "https://www.euroclubindex.com/wp-json/happyhorizon/v1/get-module-latest-ranking/?ppp=-1&pagination=1&search="
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])
    records = []
    for item in items:
        rd = item.get("rankData", {})
        records.append({
            "Club": rd.get("teamName"),
            "Country": rd.get("teamNation"),
            "Points": float(rd.get("Points", 0)),
        })
    df = pd.DataFrame(records).dropna(subset=["Club"])
    return df

df = fetch_club_ratings()

# ------------------ Probability Model ------------------
def draw_prob(delta, d0=0.25, dscale=800.0):
    """Draw probability as exponential decay of rating diff."""
    return d0 * np.exp(-abs(delta) / dscale)

def calibrate_k(target_delta=500.0, target_home=0.66, d0=0.25, dscale=800.0):
    """Calibrate logistic slope so that Δ=500 → 66% home win."""
    D = draw_prob(target_delta, d0, dscale)
    S_target = target_home / (1.0 - D)
    S_target = np.clip(S_target, 1e-6, 1 - 1e-6)
    return np.log(S_target / (1.0 - S_target)) / target_delta

def probs_from_ecidiff(delta, d0=0.25, dscale=800.0):
    """Return (home, draw, away) probabilities from ECI difference."""
    k = calibrate_k(500.0, 0.66, d0, dscale)
    D = draw_prob(delta, d0, dscale)
    S = 1.0 / (1.0 + np.exp(-k * delta))
    p_home = (1.0 - D) * S
    p_away = (1.0 - D) * (1.0 - S)
    total = p_home + D + p_away
    return p_home / total, D / total, p_away / total

# ------------------ Layout ------------------
tabs = st.tabs(["📊 Club Ratings", "⚽ Match Odds Calculator"])

# --- TAB 1: Ratings ---
with tabs[0]:
    st.subheader("Full Club Ratings Table")
    search = st.text_input("Search clubs or countries")
    filtered = (
        df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        if search else df
    )
    st.dataframe(filtered.sort_values("Points", ascending=False), use_container_width=True)

# --- TAB 2: Odds Calculator ---
with tabs[1]:
    st.subheader("Predict Match Odds from Ratings")

    if "home" not in st.session_state:
        st.session_state.home = df["Club"].iloc[0]
    if "away" not in st.session_state:
        st.session_state.away = df["Club"].iloc[1]

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.home = st.selectbox(
            "Select Home Club", df["Club"].unique(), index=0, key="home_team_select"
        )
    with col2:
        st.session_state.away = st.selectbox(
            "Select Away Club", df["Club"].unique(), index=1, key="away_team_select"
        )

    home_team = st.session_state.home
    away_team = st.session_state.away

    if home_team and away_team and home_team != away_team:
        home_points = df.loc[df["Club"] == home_team, "Points"].iloc[0]
        away_points = df.loc[df["Club"] == away_team, "Points"].iloc[0]
        diff = home_points - away_points

        p_home, p_draw, p_away = probs_from_ecidiff(diff)

        odds_home = 1 / p_home
        odds_draw = 1 / p_draw
        odds_away = 1 / p_away

        st.markdown(f"### Rating Difference: `{diff:.1f}`")
        st.write(f"Home ECI: {home_points:.1f}, Away ECI: {away_points:.1f}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Home Win", f"{p_home*100:.1f}%", f"Odds {odds_home:.2f}")
        col2.metric("Draw", f"{p_draw*100:.1f}%", f"Odds {odds_draw:.2f}")
        col3.metric("Away Win", f"{p_away*100:.1f}%", f"Odds {odds_away:.2f}")

        st.caption(
            "Model calibrated so Δ=500 → 66 % home win. "
            "Draw probability decays exponentially with |Δ|."
        )
    else:
        st.info("Select two different clubs to calculate odds.")
