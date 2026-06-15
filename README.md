# CS Intelligence Dashboard

CS Intelligence Dashboard is a Counter-Strike analytics dashboard that collects real match data from the PandaScore API, processes it with Python and pandas, and visualizes team performance, recent form, head-to-head results, and pre-match comparison metrics with Streamlit and Plotly.

The project is positioned as an esports analytics portfolio project, not as a betting product.

## Current Features

- Load processed Counter-Strike match data from PandaScore
- Show dataset coverage: matches, teams, tournaments, first match, latest match
- Compare two teams by matches played, wins, losses, winrate, recent form, recent winrate, and average score difference
- Visualize selected comparison metrics with Plotly
- Show head-to-head matches for the selected teams
- Show recent matches for each selected team

## Project Structure

```text
cs-intelligence-dashboard/
|-- app.py
|-- requirements.txt
|-- README.md
|-- data/
|   |-- matches.csv
|   `-- processed/
|       `-- pandascore_matches.csv
`-- scripts/
    `-- fetch_pandascore_matches.py
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## PandaScore Token

Create a local `.env` file in the project root:

```text
PANDASCORE_TOKEN=your_token_here
```

Do not commit `.env` to GitHub.

## Update Data

Fetch and process recent finished CS matches:

```bash
python scripts/fetch_pandascore_matches.py
```

The script writes:

```text
data/raw/pandascore_matches_raw.json
data/processed/pandascore_matches.csv
```

## Run Dashboard

```bash
streamlit run app.py
```

The dashboard reads:

```text
data/processed/pandascore_matches.csv
```

## Roadmap

- Tournament and date filters
- Stronger recent-form metrics for last 5/10 matches
- Opponent-strength indicators
- Team detail pages
- Map pool analysis
- Player statistics
- AI-generated analytical summaries
