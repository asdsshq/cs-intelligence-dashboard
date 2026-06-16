import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = (os.getenv("GRID_API_KEY") or "").strip()

if not API_KEY:
    raise ValueError("GRID_API_KEY not found. Add it to your .env file.")

FULL_ACCESS_URL = "https://api.grid.gg/central-data/graphql"
OPEN_ACCESS_URL = "https://api-op.grid.gg/central-data/graphql"
RAW_DIR = Path("data/raw")


SERIES_QUERY = """
query GetSeries($from: String!, $to: String!, $first: Int!, $titleId: ID) {
  allSeries(
    first: $first
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch visible GRID Central Data series ids."
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        default="2026-06-01T00:00:00+00:00",
        help="Start of scheduled time window."
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        default="2026-06-16T23:59:59+00:00",
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
        data = graphql_request(
            endpoint,
            SERIES_QUERY,
            {
                "from": args.from_date,
                "to": args.to_date,
                "first": first,
                "titleId": args.title_id
            }
        )
        output_path = save_json(RAW_DIR / "grid_series_index_raw.json", data)
        print_series_summary(data)

    print()
    print("Saved:")
    print(output_path)


if __name__ == "__main__":
    main()
