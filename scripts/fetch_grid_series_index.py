import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
import pandas as pd


load_dotenv()

API_KEY = (os.getenv("GRID_API_KEY") or "").strip()

if not API_KEY:
    raise ValueError("GRID_API_KEY not found. Add it to your .env file.")

FULL_ACCESS_URL = "https://api.grid.gg/central-data/graphql"
OPEN_ACCESS_URL = "https://api-op.grid.gg/central-data/graphql"
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


SERIES_QUERY = """
query GetSeries(
  $from: String!,
  $to: String!,
  $first: Int!,
  $titleId: ID,
  $after: String
) {
  allSeries(
    first: $first
    after: $after
    filter: {
      titleId: $titleId
      startTimeScheduled: {
        gte: $from
        lte: $to
      }
    }
    orderBy: StartTimeScheduled
    orderDirection: DESC
  ) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        startTimeScheduled
        type
        workflowStatus
        title {
          id
          name
        }
        tournament {
          id
          name
          nameShortened
        }
        format {
          id
          name
          nameShortened
        }
        teams {
          baseInfo {
            id
            name
            nameShortened
          }
          scoreAdvantage
        }
      }
    }
  }
}
"""


TITLES_QUERY = """
query GetTitles {
  titles {
    id
    name
  }
}
"""


INTROSPECTION_QUERY = """
query IntrospectType($name: String!) {
  __type(name: $name) {
    name
    kind
    inputFields {
      name
      type {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
          }
        }
      }
    }
    fields {
      name
      type {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
          }
        }
      }
    }
  }
}
"""


def graphql_request(endpoint: str, query: str, variables: dict | None = None) -> dict:
    response = requests.post(
        endpoint,
        headers={
            "x-api-key": API_KEY,
            "content-type": "application/json"
        },
        json={
            "query": query,
            "variables": variables or {}
        },
        timeout=60
    )

    print("Request URL:", response.url)
    print("Status code:", response.status_code)
    print("Content type:", response.headers.get("content-type", "unknown"))

    if not response.ok:
        print()
        print("GRID error response:")
        print(response.text[:1000] or "<empty response body>")
        response.raise_for_status()

    data = response.json()

    if data.get("errors"):
        print()
        print("GRID GraphQL errors:")
        print(json.dumps(data["errors"], ensure_ascii=False, indent=2)[:4000])

    return data


def save_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return path


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if value.lower() in ["", "none", "nan", "null", "<null>"]:
        return None

    return value


def team_name(team: dict | None) -> str | None:
    if not team:
        return None

    return clean_text(team.get("name") or team.get("nameShortened"))


def normalize_series(data: dict, include_test_data: bool = False) -> pd.DataFrame:
    all_series = (data.get("data") or {}).get("allSeries") or {}
    edges = all_series.get("edges") or []
    rows = []

    for edge in edges:
        node = edge.get("node") or {}
        teams = node.get("teams") or []
        team_1 = (teams[0].get("baseInfo") or {}) if len(teams) > 0 else {}
        team_2 = (teams[1].get("baseInfo") or {}) if len(teams) > 1 else {}
        title = node.get("title") or {}
        tournament = node.get("tournament") or {}
        series_format = node.get("format") or {}

        rows.append({
            "series_id": node.get("id"),
            "start_time_scheduled": node.get("startTimeScheduled"),
            "date": node.get("startTimeScheduled"),
            "team_1": team_name(team_1),
            "team_2": team_name(team_2),
            "team_1_id": team_1.get("id"),
            "team_2_id": team_2.get("id"),
            "title": clean_text(title.get("name")),
            "title_id": title.get("id"),
            "tournament": clean_text(tournament.get("name")),
            "tournament_short_name": clean_text(tournament.get("nameShortened")),
            "tournament_id": tournament.get("id"),
            "format": clean_text(series_format.get("name")),
            "format_short_name": clean_text(series_format.get("nameShortened")),
            "format_id": series_format.get("id"),
            "series_type": clean_text(node.get("type")),
            "workflow_status": clean_text(node.get("workflowStatus")),
            "source": "GRID"
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
        utc=True
    ).dt.date

    text_columns = [
        "team_1",
        "team_2",
        "title",
        "tournament",
        "tournament_short_name",
        "format",
        "format_short_name",
        "series_type",
        "workflow_status"
    ]

    for column in text_columns:
        df[column] = df[column].apply(clean_text)

    if not include_test_data:
        df = df[
            (df["tournament"] != "GRID-TEST") &
            (df["series_type"] != "LOOPFEED")
        ].copy()

    return df


def save_processed_series(
    data: dict,
    include_test_data: bool = False
) -> tuple[Path, pd.DataFrame]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = normalize_series(data, include_test_data=include_test_data)
    output_path = PROCESSED_DIR / "grid_series.csv"
    df.to_csv(output_path, index=False)

    return output_path, df


def print_series_summary(data: dict) -> None:
    all_series = (data.get("data") or {}).get("allSeries") or {}
    edges = all_series.get("edges") or []

    print()
    print("Series summary:")
    print("Total count:", all_series.get("totalCount"))
    print("Returned:", len(edges))

    for edge in edges[:10]:
        node = edge.get("node") or {}
        teams = node.get("teams") or []
        team_names = " vs ".join(
            (team.get("baseInfo") or {}).get("name")
            or (team.get("baseInfo") or {}).get("nameShortened")
            or str((team.get("baseInfo") or {}).get("id"))
            for team in teams
        )
        tournament = node.get("tournament") or {}
        print(
            f"- {node.get('id')} | "
            f"{node.get('startTimeScheduled')} | "
            f"{team_names or 'TBD'} | "
            f"{tournament.get('name') or 'Unknown tournament'}"
        )


def print_titles_summary(data: dict) -> None:
    titles = (data.get("data") or {}).get("titles") or []

    print()
    print("Titles:")

    for title in titles:
        print(f"- {title.get('id')} | {title.get('name')}")


def print_introspection_summary(data: dict) -> None:
    type_info = (data.get("data") or {}).get("__type") or {}
    input_fields = type_info.get("inputFields") or []
    fields = type_info.get("fields") or []

    print()
    print("Type:")
    print(type_info.get("name"), type_info.get("kind"))

    for field in input_fields or fields:
        print(f"- {field.get('name')}")


def utc_timestamp(days_offset: int = 0, end_of_day: bool = False) -> str:
    date_value = datetime.now(timezone.utc) + timedelta(days=days_offset)

    if end_of_day:
        date_value = date_value.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        date_value = date_value.replace(hour=0, minute=0, second=0, microsecond=0)

    return date_value.isoformat()


def merge_series_pages(pages: list[dict]) -> dict:
    if not pages:
        return {"data": {"allSeries": {"totalCount": 0, "edges": []}}}

    first_page_series = (pages[0].get("data") or {}).get("allSeries") or {}
    last_page_series = (pages[-1].get("data") or {}).get("allSeries") or {}
    edges = []

    for page in pages:
        page_series = (page.get("data") or {}).get("allSeries") or {}
        edges.extend(page_series.get("edges") or [])

    return {
        "data": {
            "allSeries": {
                "totalCount": first_page_series.get("totalCount"),
                "pageInfo": last_page_series.get("pageInfo"),
                "edges": edges
            }
        }
    }


def fetch_series_pages(
    endpoint: str,
    from_date: str,
    to_date: str,
    first: int,
    title_id: str,
    all_pages: bool,
    max_pages: int
) -> dict:
    pages = []
    after = None

    for page_number in range(1, max_pages + 1):
        data = graphql_request(
            endpoint,
            SERIES_QUERY,
            {
                "from": from_date,
                "to": to_date,
                "first": first,
                "titleId": title_id,
                "after": after
            }
        )

        pages.append(data)

        all_series = (data.get("data") or {}).get("allSeries") or {}
        page_info = all_series.get("pageInfo") or {}

        if data.get("errors") or not all_pages or not page_info.get("hasNextPage"):
            break

        after = page_info.get("endCursor")

        if not after:
            break

        print(f"Loaded GRID series page {page_number}")

    return merge_series_pages(pages)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch visible GRID Central Data series ids."
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        default=utc_timestamp(days_offset=-14),
        help="Start of scheduled time window."
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        default=utc_timestamp(end_of_day=True),
        help="End of scheduled time window."
    )
    parser.add_argument(
        "--first",
        type=int,
        default=10,
        help="Number of series to return, maximum 50."
    )
    parser.add_argument(
        "--title-id",
        default="28",
        help="GRID title id to filter by. Counter Strike 2 is 28."
    )
    parser.add_argument(
        "--open-access",
        action="store_true",
        help="Use the Open Access Central Data endpoint."
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Fetch all available pages for the selected time window."
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Safety cap for paginated series requests."
    )
    parser.add_argument(
        "--include-test-data",
        action="store_true",
        help="Keep GRID-TEST and LOOPFEED rows in the processed CSV."
    )
    parser.add_argument(
        "--titles",
        action="store_true",
        help="Fetch visible titles instead of series."
    )
    parser.add_argument(
        "--introspect",
        default=None,
        help="Print GraphQL schema fields for a type, for example SeriesFilter."
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = OPEN_ACCESS_URL if args.open_access else FULL_ACCESS_URL

    if args.introspect:
        data = graphql_request(
            endpoint,
            INTROSPECTION_QUERY,
            {"name": args.introspect}
        )
        output_path = save_json(
            RAW_DIR / f"grid_introspection_{args.introspect}.json",
            data
        )
        print_introspection_summary(data)
    elif args.titles:
        data = graphql_request(endpoint, TITLES_QUERY)
        output_path = save_json(RAW_DIR / "grid_titles_raw.json", data)
        print_titles_summary(data)
    else:
        first = max(1, min(args.first, 50))
        data = fetch_series_pages(
            endpoint,
            args.from_date,
            args.to_date,
            first,
            args.title_id,
            args.all_pages,
            max(1, args.max_pages)
        )
        output_path = save_json(RAW_DIR / "grid_series_index_raw.json", data)
        processed_path, df = save_processed_series(
            data,
            include_test_data=args.include_test_data
        )
        print_series_summary(data)

    print()
    print("Saved:")
    print(output_path)

    if not args.introspect and not args.titles:
        print(processed_path)
        print()
        print(f"Processed rows: {len(df)}")


if __name__ == "__main__":
    main()
