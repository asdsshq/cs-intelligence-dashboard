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


@st.cache_data
def load_matches():
    return pd.read_csv("data/matches.csv")


def build_team_view(matches: pd.DataFrame) -> pd.DataFrame:
    team_1_view = matches[[
        "date", "team_1", "team_2", "map",
        "team_1_score", "team_2_score", "winner", "tournament"
    ]].copy()

    team_1_view.columns = [
        "date", "team", "opponent", "map",
        "rounds_for", "rounds_against", "winner", "tournament"
    ]

    team_2_view = matches[[
        "date", "team_2", "team_1", "map",
        "team_2_score", "team_1_score", "winner", "tournament"
    ]].copy()

    team_2_view.columns = [
        "date", "team", "opponent", "map",
        "rounds_for", "rounds_against", "winner", "tournament"
    ]

    team_view = pd.concat([team_1_view, team_2_view], ignore_index=True)
    team_view["result"] = team_view.apply(
        lambda row: "Win" if row["team"] == row["winner"] else "Loss",
        axis=1
    )

    return team_view


def get_team_stats(team_view: pd.DataFrame, team_name: str) -> dict:
    team_matches = team_view[team_view["team"] == team_name]

    matches_played = len(team_matches)
    wins = len(team_matches[team_matches["result"] == "Win"])
    losses = len(team_matches[team_matches["result"] == "Loss"])
    winrate = wins / matches_played * 100 if matches_played > 0 else 0

    avg_rounds_for = team_matches["rounds_for"].mean() if matches_played > 0 else 0
    avg_rounds_against = team_matches["rounds_against"].mean() if matches_played > 0 else 0

    map_stats = (
        team_matches
        .groupby("map")
        .agg(
            matches=("map", "count"),
            wins=("result", lambda x: (x == "Win").sum())
        )
        .reset_index()
    )

    if not map_stats.empty:
        map_stats["winrate"] = map_stats["wins"] / map_stats["matches"] * 100
        best_map = map_stats.sort_values(
            by=["winrate", "matches"],
            ascending=False
        ).iloc[0]["map"]
    else:
        best_map = "No data"

    return {
        "matches_played": matches_played,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_rounds_for": avg_rounds_for,
        "avg_rounds_against": avg_rounds_against,
        "best_map": best_map,
        "team_matches": team_matches,
        "map_stats": map_stats
    }


matches = load_matches()
team_view = build_team_view(matches)

st.header("Match Data")

with st.expander("Show raw match data"):
    st.dataframe(matches, use_container_width=True)

st.header("Team Comparison")

teams = sorted(team_view["team"].unique())

col_select_1, col_select_2 = st.columns(2)

with col_select_1:
    team_a = st.selectbox("Select Team A", teams, index=0)

with col_select_2:
    default_index = 1 if len(teams) > 1 else 0
    team_b = st.selectbox("Select Team B", teams, index=default_index)

team_a_stats = get_team_stats(team_view, team_a)
team_b_stats = get_team_stats(team_view, team_b)

st.subheader(f"{team_a} vs {team_b}")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### {team_a}")
    st.metric("Matches Played", team_a_stats["matches_played"])
    st.metric("Wins", team_a_stats["wins"])
    st.metric("Losses", team_a_stats["losses"])
    st.metric("Winrate", f"{team_a_stats['winrate']:.1f}%")
    st.metric("Average Rounds Won", f"{team_a_stats['avg_rounds_for']:.1f}")
    st.metric("Average Rounds Lost", f"{team_a_stats['avg_rounds_against']:.1f}")
    st.metric("Best Map", team_a_stats["best_map"])

with col2:
    st.markdown(f"### {team_b}")
    st.metric("Matches Played", team_b_stats["matches_played"])
    st.metric("Wins", team_b_stats["wins"])
    st.metric("Losses", team_b_stats["losses"])
    st.metric("Winrate", f"{team_b_stats['winrate']:.1f}%")
    st.metric("Average Rounds Won", f"{team_b_stats['avg_rounds_for']:.1f}")
    st.metric("Average Rounds Lost", f"{team_b_stats['avg_rounds_against']:.1f}")
    st.metric("Best Map", team_b_stats["best_map"])

st.header("Head-to-Head")

h2h_matches = matches[
    (
        ((matches["team_1"] == team_a) & (matches["team_2"] == team_b)) |
        ((matches["team_1"] == team_b) & (matches["team_2"] == team_a))
    )
]

if h2h_matches.empty:
    st.info("No head-to-head matches found for these teams.")
else:
    st.dataframe(h2h_matches, use_container_width=True)

    team_a_h2h_wins = len(h2h_matches[h2h_matches["winner"] == team_a])
    team_b_h2h_wins = len(h2h_matches[h2h_matches["winner"] == team_b])

    col_h2h_1, col_h2h_2 = st.columns(2)

    with col_h2h_1:
        st.metric(f"{team_a} H2H Wins", team_a_h2h_wins)

    with col_h2h_2:
        st.metric(f"{team_b} H2H Wins", team_b_h2h_wins)

st.header("Map Statistics")

col_map_1, col_map_2 = st.columns(2)

with col_map_1:
    st.markdown(f"### {team_a} Map Pool")
    st.dataframe(team_a_stats["map_stats"], use_container_width=True)

with col_map_2:
    st.markdown(f"### {team_b} Map Pool")
    st.dataframe(team_b_stats["map_stats"], use_container_width=True)