from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path("data/processed/pandascore_matches.csv")


st.set_page_config(
    page_title="CS Intelligence Dashboard",
    page_icon="🎯",
    layout="wide"
)


@st.cache_data
def load_matches() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error(
            "PandaScore data file not found. "
            "Run `python scripts/fetch_pandascore_matches.py` first."
        )
        st.stop()

    df = pd.read_csv(DATA_PATH)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df = df.sort_values("date", ascending=False)

    return df


def build_team_view(matches: pd.DataFrame) -> pd.DataFrame:
    team_1_view = matches[[
        "match_id",
        "date",
        "team_1",
        "team_2",
        "team_1_score",
        "team_2_score",
        "winner",
        "league",
        "serie",
        "tournament",
        "event_name",
        "number_of_games"
    ]].copy()

    team_1_view.columns = [
        "match_id",
        "date",
        "team",
        "opponent",
        "score_for",
        "score_against",
        "winner",
        "league",
        "serie",
        "tournament",
        "event_name",
        "number_of_games"
    ]

    team_2_view = matches[[
        "match_id",
        "date",
        "team_2",
        "team_1",
        "team_2_score",
        "team_1_score",
        "winner",
        "league",
        "serie",
        "tournament",
        "event_name",
        "number_of_games"
    ]].copy()

    team_2_view.columns = [
        "match_id",
        "date",
        "team",
        "opponent",
        "score_for",
        "score_against",
        "winner",
        "league",
        "serie",
        "tournament",
        "event_name",
        "number_of_games"
    ]

    team_view = pd.concat([team_1_view, team_2_view], ignore_index=True)

    team_view["result"] = team_view.apply(
        lambda row: "Win" if row["team"] == row["winner"] else "Loss",
        axis=1
    )

    team_view["score_diff"] = team_view["score_for"] - team_view["score_against"]

    return team_view


def get_team_stats(team_view: pd.DataFrame, team_name: str) -> dict:
    team_matches = team_view[team_view["team"] == team_name].copy()
    team_matches = team_matches.sort_values("date", ascending=False)

    matches_played = len(team_matches)
    wins = len(team_matches[team_matches["result"] == "Win"])
    losses = len(team_matches[team_matches["result"] == "Loss"])

    winrate = wins / matches_played * 100 if matches_played > 0 else 0

    avg_score_for = team_matches["score_for"].mean() if matches_played > 0 else 0
    avg_score_against = team_matches["score_against"].mean() if matches_played > 0 else 0
    avg_score_diff = team_matches["score_diff"].mean() if matches_played > 0 else 0

    recent_matches = team_matches.head(5)
    recent_wins = len(recent_matches[recent_matches["result"] == "Win"])
    recent_winrate = recent_wins / len(recent_matches) * 100 if len(recent_matches) > 0 else 0

    recent_form = "".join(
        "W" if result == "Win" else "L"
        for result in recent_matches["result"].tolist()
    )

    return {
        "matches_played": matches_played,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_score_for": avg_score_for,
        "avg_score_against": avg_score_against,
        "avg_score_diff": avg_score_diff,
        "recent_form": recent_form,
        "recent_winrate": recent_winrate,
        "team_matches": team_matches,
        "recent_matches": recent_matches
    }


def get_head_to_head(matches: pd.DataFrame, team_a: str, team_b: str) -> pd.DataFrame:
    return matches[
        (
            ((matches["team_1"] == team_a) & (matches["team_2"] == team_b)) |
            ((matches["team_1"] == team_b) & (matches["team_2"] == team_a))
        )
    ].copy()


matches = load_matches()
team_view = build_team_view(matches)

st.title("CS Intelligence Dashboard")
st.subheader("Counter-Strike analytics and pre-match insights")

st.write(
    "This dashboard uses real match data from PandaScore API "
    "to compare teams, analyze recent form, head-to-head results, "
    "and basic pre-match indicators."
)

st.header("Dataset Overview")

total_matches = len(matches)
unique_teams = len(set(matches["team_1"]).union(set(matches["team_2"])))
unique_events = matches["event_name"].nunique()
date_min = matches["date"].min().date()
date_max = matches["date"].max().date()

col_overview_1, col_overview_2, col_overview_3, col_overview_4 = st.columns(4)

with col_overview_1:
    st.metric("Matches", total_matches)

with col_overview_2:
    st.metric("Teams", unique_teams)

with col_overview_3:
    st.metric("Events", unique_events)

with col_overview_4:
    st.metric("Date Range", f"{date_min} — {date_max}")

with st.expander("Show raw PandaScore match data"):
    st.dataframe(matches, use_container_width=True)


st.header("Team Comparison")

teams = sorted(team_view["team"].dropna().unique())

col_select_1, col_select_2 = st.columns(2)

with col_select_1:
    team_a = st.selectbox("Select Team A", teams, index=0)

with col_select_2:
    default_index = 1 if len(teams) > 1 else 0
    team_b = st.selectbox("Select Team B", teams, index=default_index)

if team_a == team_b:
    st.warning("Select two different teams for comparison.")

team_a_stats = get_team_stats(team_view, team_a)
team_b_stats = get_team_stats(team_view, team_b)

st.subheader(f"{team_a} vs {team_b}")

col_team_1, col_team_2 = st.columns(2)

with col_team_1:
    st.markdown(f"### {team_a}")
    st.metric("Matches Played", team_a_stats["matches_played"])
    st.metric("Wins", team_a_stats["wins"])
    st.metric("Losses", team_a_stats["losses"])
    st.metric("Winrate", f"{team_a_stats['winrate']:.1f}%")
    st.metric("Recent Form", team_a_stats["recent_form"] or "No data")
    st.metric("Recent Winrate", f"{team_a_stats['recent_winrate']:.1f}%")
    st.metric("Average Score For", f"{team_a_stats['avg_score_for']:.2f}")
    st.metric("Average Score Against", f"{team_a_stats['avg_score_against']:.2f}")
    st.metric("Average Score Difference", f"{team_a_stats['avg_score_diff']:.2f}")

with col_team_2:
    st.markdown(f"### {team_b}")
    st.metric("Matches Played", team_b_stats["matches_played"])
    st.metric("Wins", team_b_stats["wins"])
    st.metric("Losses", team_b_stats["losses"])
    st.metric("Winrate", f"{team_b_stats['winrate']:.1f}%")
    st.metric("Recent Form", team_b_stats["recent_form"] or "No data")
    st.metric("Recent Winrate", f"{team_b_stats['recent_winrate']:.1f}%")
    st.metric("Average Score For", f"{team_b_stats['avg_score_for']:.2f}")
    st.metric("Average Score Against", f"{team_b_stats['avg_score_against']:.2f}")
    st.metric("Average Score Difference", f"{team_b_stats['avg_score_diff']:.2f}")


st.header("Comparison Chart")

comparison_df = pd.DataFrame([
    {
        "team": team_a,
        "matches_played": team_a_stats["matches_played"],
        "wins": team_a_stats["wins"],
        "losses": team_a_stats["losses"],
        "winrate": team_a_stats["winrate"],
        "recent_winrate": team_a_stats["recent_winrate"],
        "avg_score_diff": team_a_stats["avg_score_diff"]
    },
    {
        "team": team_b,
        "matches_played": team_b_stats["matches_played"],
        "wins": team_b_stats["wins"],
        "losses": team_b_stats["losses"],
        "winrate": team_b_stats["winrate"],
        "recent_winrate": team_b_stats["recent_winrate"],
        "avg_score_diff": team_b_stats["avg_score_diff"]
    }
])

metric_to_plot = st.selectbox(
    "Select metric to visualize",
    [
        "winrate",
        "recent_winrate",
        "matches_played",
        "wins",
        "losses",
        "avg_score_diff"
    ]
)

fig = px.bar(
    comparison_df,
    x="team",
    y=metric_to_plot,
    text=metric_to_plot,
    title=f"{metric_to_plot.replace('_', ' ').title()} Comparison"
)

st.plotly_chart(fig, use_container_width=True)


st.header("Head-to-Head")

h2h_matches = get_head_to_head(matches, team_a, team_b)

if h2h_matches.empty:
    st.info("No head-to-head matches found for these teams in the current dataset.")
else:
    h2h_matches = h2h_matches.sort_values("date", ascending=False)

    team_a_h2h_wins = len(h2h_matches[h2h_matches["winner"] == team_a])
    team_b_h2h_wins = len(h2h_matches[h2h_matches["winner"] == team_b])

    col_h2h_1, col_h2h_2, col_h2h_3 = st.columns(3)

    with col_h2h_1:
        st.metric("H2H Matches", len(h2h_matches))

    with col_h2h_2:
        st.metric(f"{team_a} H2H Wins", team_a_h2h_wins)

    with col_h2h_3:
        st.metric(f"{team_b} H2H Wins", team_b_h2h_wins)

    st.dataframe(
        h2h_matches[[
            "date",
            "team_1",
            "team_2",
            "team_1_score",
            "team_2_score",
            "winner",
            "event_name",
            "number_of_games"
        ]],
        use_container_width=True
    )


st.header("Recent Matches")

col_recent_1, col_recent_2 = st.columns(2)

with col_recent_1:
    st.markdown(f"### {team_a} Recent Matches")
    st.dataframe(
        team_a_stats["recent_matches"][[
            "date",
            "team",
            "opponent",
            "score_for",
            "score_against",
            "result",
            "event_name"
        ]],
        use_container_width=True
    )

with col_recent_2:
    st.markdown(f"### {team_b} Recent Matches")
    st.dataframe(
        team_b_stats["recent_matches"][[
            "date",
            "team",
            "opponent",
            "score_for",
            "score_against",
            "result",
            "event_name"
        ]],
        use_container_width=True
    )