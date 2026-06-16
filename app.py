from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path("data/processed/pandascore_matches.csv")
GRID_SERIES_PATH = Path("data/processed/grid_series.csv")
TEAM_COLUMNS = ["team_1", "team_2", "winner"]
SCORE_COLUMNS = ["team_1_score", "team_2_score", "number_of_games"]


st.set_page_config(
    page_title="CS Intelligence Dashboard",
    page_icon="🎯",
    layout="wide"
)


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1240px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
    }

    [data-testid="stMetricLabel"] p {
        color: #475569;
        font-size: 0.84rem;
    }

    [data-testid="stMetricValue"] {
        color: #0f172a;
        font-weight: 700;
    }

    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }

    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
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

    for column in TEAM_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()
            df[column] = df[column].replace({"": pd.NA})

    for column in SCORE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.sort_values("date", ascending=False)

    return df


@st.cache_data
def load_grid_series() -> pd.DataFrame:
    if not GRID_SERIES_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(GRID_SERIES_PATH)

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
    team_view = team_view.dropna(subset=["team", "opponent", "winner"])

    team_view["result"] = team_view["team"].eq(team_view["winner"]).map({
        True: "Win",
        False: "Loss"
    })

    team_view["score_diff"] = team_view["score_for"] - team_view["score_against"]

    return team_view


def filter_matches(
    matches: pd.DataFrame,
    start_date,
    end_date,
    tournaments: list[str]
) -> pd.DataFrame:
    filtered = matches.copy()
    match_dates = filtered["date"].dt.date

    filtered = filtered[
        (match_dates >= start_date) &
        (match_dates <= end_date)
    ].copy()

    if tournaments:
        filtered = filtered[filtered["tournament"].isin(tournaments)].copy()

    return filtered


def filter_grid_series(
    grid_series: pd.DataFrame,
    start_date,
    end_date
) -> pd.DataFrame:
    if grid_series.empty:
        return grid_series

    series_dates = grid_series["date"].dt.date

    return grid_series[
        (series_dates >= start_date) &
        (series_dates <= end_date)
    ].copy()


def get_team_stats(
    team_view: pd.DataFrame,
    team_name: str,
    recent_limit: int
) -> dict:
    team_matches = team_view[team_view["team"] == team_name].copy()
    team_matches = team_matches.sort_values("date", ascending=False)

    matches_played = len(team_matches)
    wins = len(team_matches[team_matches["result"] == "Win"])
    losses = len(team_matches[team_matches["result"] == "Loss"])

    winrate = wins / matches_played * 100 if matches_played > 0 else 0

    avg_score_for = team_matches["score_for"].mean() if matches_played > 0 else 0
    avg_score_against = team_matches["score_against"].mean() if matches_played > 0 else 0
    avg_score_diff = team_matches["score_diff"].mean() if matches_played > 0 else 0

    recent_matches = team_matches.head(recent_limit)
    recent_wins = len(recent_matches[recent_matches["result"] == "Win"])
    recent_winrate = recent_wins / len(recent_matches) * 100 if len(recent_matches) > 0 else 0

    recent_form = " ".join(
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


def preferred_team_index(
    teams: list[str],
    preferred_names: list[str],
    fallback_index: int = 0
) -> int:
    for team_name in preferred_names:
        if team_name in teams:
            return teams.index(team_name)

    return fallback_index


def default_team_indices(teams: list[str]) -> tuple[int, int]:
    team_a_index = preferred_team_index(teams, ["Natus Vincere", "NAVI"], 0)
    team_b_fallback = 1 if len(teams) > 1 else 0
    team_b_index = preferred_team_index(teams, ["Vitality", "G2"], team_b_fallback)

    if team_a_index == team_b_index and len(teams) > 1:
        team_b_index = (team_a_index + 1) % len(teams)

    return team_a_index, team_b_index


def metric_delta(value_a: float, value_b: float) -> float:
    return value_a - value_b


def render_team_metrics(team_name: str, stats: dict, opponent_stats: dict) -> None:
    st.markdown(f"### {team_name}")
    st.metric("Matches", stats["matches_played"])
    st.metric("Wins", stats["wins"])
    st.metric("Losses", stats["losses"])
    st.metric(
        "Winrate",
        f"{stats['winrate']:.1f}%",
        delta=f"{metric_delta(stats['winrate'], opponent_stats['winrate']):+.1f} pp"
    )
    st.metric("Recent Form", stats["recent_form"] or "No data")
    st.metric(
        "Recent Winrate",
        f"{stats['recent_winrate']:.1f}%",
        delta=f"{metric_delta(stats['recent_winrate'], opponent_stats['recent_winrate']):+.1f} pp"
    )
    st.metric("Avg Score For", f"{stats['avg_score_for']:.2f}")
    st.metric("Avg Score Against", f"{stats['avg_score_against']:.2f}")
    st.metric(
        "Avg Score Diff",
        f"{stats['avg_score_diff']:.2f}",
        delta=f"{metric_delta(stats['avg_score_diff'], opponent_stats['avg_score_diff']):+.2f}"
    )


def build_pre_match_summary(
    team_a: str,
    team_b: str,
    team_a_stats: dict,
    team_b_stats: dict,
    h2h_matches: pd.DataFrame
) -> str:
    lines = []

    if team_a_stats["recent_winrate"] > team_b_stats["recent_winrate"]:
        lines.append(
            f"{team_a} has the stronger recent form "
            f"({team_a_stats['recent_winrate']:.1f}% vs {team_b_stats['recent_winrate']:.1f}%)."
        )
    elif team_b_stats["recent_winrate"] > team_a_stats["recent_winrate"]:
        lines.append(
            f"{team_b} has the stronger recent form "
            f"({team_b_stats['recent_winrate']:.1f}% vs {team_a_stats['recent_winrate']:.1f}%)."
        )
    else:
        lines.append("Both teams have the same recent winrate in the selected window.")

    if team_a_stats["winrate"] > team_b_stats["winrate"]:
        lines.append(f"{team_a} also has the better overall winrate in the filtered dataset.")
    elif team_b_stats["winrate"] > team_a_stats["winrate"]:
        lines.append(f"{team_b} has the better overall winrate in the filtered dataset.")
    else:
        lines.append("Overall winrate is even in the filtered dataset.")

    if h2h_matches.empty:
        lines.append("No head-to-head matches are available in the current filter.")
    else:
        team_a_h2h_wins = len(h2h_matches[h2h_matches["winner"] == team_a])
        team_b_h2h_wins = len(h2h_matches[h2h_matches["winner"] == team_b])
        lines.append(
            f"Head-to-head sample: {len(h2h_matches)} matches, "
            f"{team_a} {team_a_h2h_wins}-{team_b_h2h_wins} {team_b}."
        )

    return " ".join(lines)


matches_all = load_matches()
grid_series_all = load_grid_series()

st.title("CS Intelligence Dashboard")
st.caption("Counter-Strike analytics and pre-match team comparison")

date_min_all = matches_all["date"].min().date()
date_max_all = matches_all["date"].max().date()

st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Match dates",
    value=(date_min_all, date_max_all),
    min_value=date_min_all,
    max_value=date_max_all
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = date_min_all, date_max_all

tournament_options = sorted(matches_all["tournament"].dropna().unique().tolist())
selected_tournaments = st.sidebar.multiselect(
    "Tournaments",
    tournament_options,
    default=[]
)

recent_limit = st.sidebar.slider(
    "Recent match window",
    min_value=3,
    max_value=10,
    value=5
)

matches = filter_matches(
    matches_all,
    start_date,
    end_date,
    selected_tournaments
)

if matches.empty:
    st.warning("No PandaScore matches found for the selected filters.")
    st.stop()

grid_series = filter_grid_series(grid_series_all, start_date, end_date)
team_view = build_team_view(matches)
teams = sorted(team_view["team"].dropna().unique().tolist())

if len(teams) < 2:
    st.warning("Not enough teams found for comparison in the selected filters.")
    st.stop()

team_a_index, team_b_index = default_team_indices(teams)

st.sidebar.header("Comparison")
team_a = st.sidebar.selectbox("Team A", teams, index=team_a_index)
team_b = st.sidebar.selectbox("Team B", teams, index=team_b_index)

if team_a == team_b:
    st.warning("Select two different teams for comparison.")
    st.stop()

team_a_stats = get_team_stats(team_view, team_a, recent_limit)
team_b_stats = get_team_stats(team_view, team_b, recent_limit)
h2h_matches = get_head_to_head(matches, team_a, team_b)

overview_tab, comparison_tab, history_tab, grid_tab = st.tabs([
    "Overview",
    "Team Comparison",
    "Match History",
    "GRID Metadata"
])

with overview_tab:
    st.header("Dataset Overview")

    total_matches = len(matches)
    unique_teams = team_view["team"].nunique()
    unique_tournaments = matches["tournament"].nunique()
    date_min = matches["date"].min().date().isoformat()
    date_max = matches["date"].max().date().isoformat()

    col_overview_1, col_overview_2, col_overview_3 = st.columns(3)

    with col_overview_1:
        st.metric("Matches", total_matches)

    with col_overview_2:
        st.metric("Teams", unique_teams)

    with col_overview_3:
        st.metric("Tournaments", unique_tournaments)

    st.caption(f"Match coverage: {date_min} to {date_max}")

    st.subheader(f"{team_a} vs {team_b}")
    st.info(build_pre_match_summary(
        team_a,
        team_b,
        team_a_stats,
        team_b_stats,
        h2h_matches
    ))

    with st.expander("Show PandaScore match data"):
        st.dataframe(matches, width="stretch")


with comparison_tab:
    st.header("Team Comparison")

    col_team_1, col_team_2 = st.columns(2)

    with col_team_1:
        render_team_metrics(team_a, team_a_stats, team_b_stats)

    with col_team_2:
        render_team_metrics(team_b, team_b_stats, team_a_stats)

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

    metric_options = {
        "winrate": "Winrate",
        "recent_winrate": "Recent Winrate",
        "matches_played": "Matches Played",
        "wins": "Wins",
        "losses": "Losses",
        "avg_score_diff": "Average Score Difference"
    }

    metric_to_plot = st.selectbox(
        "Metric",
        list(metric_options.keys()),
        format_func=lambda value: metric_options[value]
    )

    fig = px.bar(
        comparison_df,
        x="team",
        y=metric_to_plot,
        text=metric_to_plot,
        color="team",
        color_discrete_sequence=["#0891b2", "#16a34a"],
        title=f"{metric_options[metric_to_plot]} Comparison",
        labels={
            "team": "Team",
            metric_to_plot: metric_options[metric_to_plot]
        }
    )

    texttemplate = "%{text:.1f}" if metric_to_plot in [
        "winrate",
        "recent_winrate",
        "avg_score_diff"
    ] else "%{text:.0f}"

    fig.update_traces(texttemplate=texttemplate, textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title=metric_options[metric_to_plot],
        showlegend=False
    )

    st.plotly_chart(fig, width="stretch")


with history_tab:
    st.header("Head-to-Head")

    if h2h_matches.empty:
        st.info("No head-to-head matches found for these teams in the current filters.")
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
            width="stretch"
        )

    st.header("Recent Matches")

    col_recent_1, col_recent_2 = st.columns(2)

    with col_recent_1:
        st.markdown(f"### {team_a}")
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
            width="stretch"
        )

    with col_recent_2:
        st.markdown(f"### {team_b}")
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
            width="stretch"
        )


with grid_tab:
    st.header("GRID Series Metadata")

    if grid_series.empty:
        st.info("GRID series metadata is unavailable for the selected dates.")
    else:
        grid_teams = pd.concat([
            grid_series["team_1"],
            grid_series["team_2"]
        ]).dropna().nunique()
        grid_date_min = grid_series["date"].min().date().isoformat()
        grid_date_max = grid_series["date"].max().date().isoformat()

        col_grid_1, col_grid_2, col_grid_3 = st.columns(3)

        with col_grid_1:
            st.metric("GRID Series", len(grid_series))

        with col_grid_2:
            st.metric("GRID Teams", grid_teams)

        with col_grid_3:
            st.metric("GRID Tournaments", grid_series["tournament"].nunique())

        st.caption(f"GRID schedule coverage: {grid_date_min} to {grid_date_max}")

        st.dataframe(
            grid_series[[
                "series_id",
                "date",
                "team_1",
                "team_2",
                "tournament",
                "format",
                "workflow_status"
            ]],
            width="stretch"
        )
