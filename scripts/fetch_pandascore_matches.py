import os
import json
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("PANDASCORE_TOKEN")

if not TOKEN:
    raise ValueError("PANDASCORE_TOKEN not found. Add it to your .env file.")

BASE_URL = "https://api.pandascore.co/csgo/matches/past"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def get_opponent(match: dict, index: int) -> dict:
    opponents = match.get("opponents", [])

    if len(opponents) <= index:
        return {}

    opponent_data = opponents[index].get("opponent")

    if not opponent_data:
        return {}

    return opponent_data


def get_team_score(match: dict, team_id: int) -> int | None:
    results = match.get("results", [])

    for result in results:
        if result.get("team_id") == team_id:
            return result.get("score")

    return None


def get_match_date(match: dict) -> str | None:
    return (
        match.get("end_at")
        or match.get("begin_at")
        or match.get("scheduled_at")
    )


def clean_text(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in ["", "none", "nan", "null", "<null>"]:
        return None

    return value


def fetch_matches(pages: int = 5, page_size: int = 100) -> list[dict]:
    all_matches = []

    for page in range(1, pages + 1):
        params = {
            "page[number]": page,
            "page[size]": page_size,
            "sort": "-end_at",
            "filter[status]": "finished"
        }

        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params=params,
            timeout=30
        )

        print("Request URL:", response.url)
        print("Status code:", response.status_code)

        response.raise_for_status()

        page_matches = response.json()

        if not page_matches:
            break

        all_matches.extend(page_matches)

        print(f"Loaded page {page}: {len(page_matches)} matches")

    return all_matches


def normalize_matches(matches: list[dict]) -> pd.DataFrame:
    rows = []

    for match in matches:
        team_1 = get_opponent(match, 0)
        team_2 = get_opponent(match, 1)

        team_1_id = team_1.get("id")
        team_2_id = team_2.get("id")

        team_1_score = get_team_score(match, team_1_id)
        team_2_score = get_team_score(match, team_2_id)

        winner = match.get("winner") or {}

        row = {
            "match_id": match.get("id"),
            "date": get_match_date(match),
            "begin_at": match.get("begin_at"),
            "end_at": match.get("end_at"),

            "team_1": team_1.get("name"),
            "team_2": team_2.get("name"),
            "team_1_id": team_1_id,
            "team_2_id": team_2_id,

            "team_1_score": team_1_score,
            "team_2_score": team_2_score,

            "winner": winner.get("name") if isinstance(winner, dict) else None,
            "winner_id": match.get("winner_id"),

            "status": match.get("status"),
            "match_type": match.get("match_type"),
            "number_of_games": match.get("number_of_games"),

            "league": (match.get("league") or {}).get("name"),
            "serie": (match.get("serie") or {}).get("name"),
            "tournament": (match.get("tournament") or {}).get("name"),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    print()
    print("Status distribution:")
    print(df["status"].value_counts(dropna=False))

    df = df[
        (df["status"] == "finished") &
        (df["date"].notna()) &
        (df["team_1"].notna()) &
        (df["team_2"].notna()) &
        (df["team_1_score"].notna()) &
        (df["team_2_score"].notna()) &
        (df["winner"].notna())
    ].copy()

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date", ascending=False)

    integer_columns = [
        "match_id",
        "team_1_id",
        "team_2_id",
        "team_1_score",
        "team_2_score",
        "winner_id",
        "number_of_games"
    ]

    for column in integer_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            ).astype("Int64")

    text_columns = [
        "league",
        "serie",
        "tournament"
    ]

    for column in text_columns:
        df[column] = df[column].apply(clean_text)

    def build_event_name(row):
        parts = [
            clean_text(row["league"]),
            clean_text(row["serie"]),
            clean_text(row["tournament"])
        ]

        clean_parts = [str(part) for part in parts if part is not None]

        if not clean_parts:
            return "Unknown event"

        return " / ".join(clean_parts)

    df["event_name"] = df.apply(build_event_name, axis=1)

    df["league"] = df["league"].fillna("Unknown league")
    df["serie"] = df["serie"].fillna("—")
    df["tournament"] = df["tournament"].fillna("Unknown tournament")

    return df


def main():
    matches = fetch_matches(pages=5, page_size=100)

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    with open("data/raw/pandascore_matches_raw.json", "w", encoding="utf-8") as file:
        json.dump(matches, file, ensure_ascii=False, indent=2)

    df = normalize_matches(matches)

    df.to_csv("data/processed/pandascore_matches.csv", index=False)

    print()
    print("Saved:")
    print("data/raw/pandascore_matches_raw.json")
    print("data/processed/pandascore_matches.csv")
    print()
    print(f"Total raw matches: {len(matches)}")
    print(f"Valid matches: {len(df)}")
    print()
    print(df.head())


if __name__ == "__main__":
    main()