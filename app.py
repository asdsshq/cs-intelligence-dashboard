import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="CS Intelligence Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.title("CS Intelligence Dashboard")
st.subheader("Counter-Strike analytics and pre-match insights")

st.write(
    "This dashboard provides team comparison, player statistics, "
    "map pool analysis, recent form tracking, and pre-match analytical summaries."
)

matches = pd.read_csv("data/matches.csv")

st.header("Match Data")
st.dataframe(matches)

st.header("Team Comparison")

teams = sorted(set(matches["team_1"]).union(set(matches["team_2"])))

team_a = st.selectbox("Select Team A", teams)
team_b = st.selectbox("Select Team B", teams, index=1)

team_a_matches = matches[
    (matches["team_1"] == team_a) | (matches["team_2"] == team_a)
]

team_b_matches = matches[
    (matches["team_1"] == team_b) | (matches["team_2"] == team_b)
]

team_a_wins = len(team_a_matches[team_a_matches["winner"] == team_a])
team_b_wins = len(team_b_matches[team_b_matches["winner"] == team_b])

team_a_winrate = team_a_wins / len(team_a_matches) * 100 if len(team_a_matches) > 0 else 0
team_b_winrate = team_b_wins / len(team_b_matches) * 100 if len(team_b_matches) > 0 else 0

col1, col2 = st.columns(2)

with col1:
    st.metric(f"{team_a} Winrate", f"{team_a_winrate:.1f}%")
    st.dataframe(team_a_matches)

with col2:
    st.metric(f"{team_b} Winrate", f"{team_b_winrate:.1f}%")
    st.dataframe(team_b_matches)