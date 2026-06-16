# CS Intelligence Dashboard

CS Intelligence Dashboard is a Counter-Strike analytics dashboard that collects real match data from the PandaScore API, processes it with Python and pandas, and visualizes team performance, recent form, head-to-head results, and pre-match comparison metrics with Streamlit and Plotly.

The project is positioned as an esports analytics portfolio project, not as a betting product.

## Current Features

- Load processed Counter-Strike match data from PandaScore
- Filter matches by date range and tournament
- Show dataset coverage: matches, teams, tournaments, first match, latest match
- Compare two teams by matches played, wins, losses, winrate, recent form, recent winrate, and average score difference
- Visualize selected comparison metrics with Plotly
- Show head-to-head matches for the selected teams
- Show recent matches for each selected team
- Generate a short pre-match analytical summary from filtered data
- Fetch visible Counter-Strike 2 series metadata from GRID Open Access Central Data

## Project Structure

```text
cs-intelligence-dashboard/
|-- .env.example
|-- app.py
|-- requirements.txt
|-- README.md
|-- data/
|   |-- matches.csv
|   `-- processed/
|       |-- grid_series.csv
|       `-- pandascore_matches.csv
`-- scripts/
    |-- fetch_grid_series.py
    |-- fetch_grid_series_index.py
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
GRID_API_KEY=your_grid_api_key_here
```

Do not commit `.env` to GitHub.

## Update Data

Fetch and process recent finished CS matches from PandaScore:

```bash
python scripts/fetch_pandascore_matches.py
```

The script writes:

```text
data/raw/pandascore_matches_raw.json
data/processed/pandascore_matches.csv
```

Fetch visible CS2 series metadata from GRID Open Access Central Data:

```bash
python scripts/fetch_grid_series_index.py \
  --open-access \
  --title-id 28 \
  --first 50 \
  --all-pages
```

The script writes:

```text
data/raw/grid_series_index_raw.json
data/processed/grid_series.csv
```

`grid_series.csv` contains GRID series metadata such as teams, scheduled time, tournament, format, title, and workflow status. It does not include match scores or in-game events unless GRID grants File Download / Live Data access.

## Run Dashboard

```bash
streamlit run app.py
```

The dashboard reads:

```text
data/processed/pandascore_matches.csv
data/processed/grid_series.csv
```

## Roadmap

- Stronger recent-form metrics for last 5/10 matches
- Opponent-strength indicators
- Team detail pages
- Map pool analysis
- Player statistics
- AI-generated analytical summaries
