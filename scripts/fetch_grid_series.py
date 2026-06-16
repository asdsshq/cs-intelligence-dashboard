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

BASE_URL = "https://api.grid.gg/file-download"
RAW_DIR = Path("data/raw")


def grid_get(url: str) -> requests.Response:
    headers = {
        "x-api-key": API_KEY
    }

    response = requests.get(
        url,
        headers=headers,
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

    return response


def parse_json_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except requests.JSONDecodeError as exc:
        raise ValueError(
            "GRID response is not valid JSON. "
            "Check whether this endpoint returns a downloadable archive instead."
        ) from exc


def fetch_available_files(series_id: str) -> dict:
    response = grid_get(f"{BASE_URL}/list/{series_id}")
    data = parse_json_response(response)

    if not isinstance(data, dict):
        raise ValueError("GRID file list response should be a JSON object.")

    return data


def download_file(full_url: str) -> bytes:
    response = grid_get(full_url)
    return response.content


def choose_file(files: list[dict], file_id: str) -> dict | None:
    for file_info in files:
        if file_info.get("id") == file_id:
            return file_info

    return None


def describe_json(data: Any) -> None:
    print()
    print("Response summary:")

    if isinstance(data, dict):
        print("Type: object")
        print("Top-level keys:", ", ".join(sorted(data.keys())))
        return

    if isinstance(data, list):
        print("Type: list")
        print("Items:", len(data))
        if data and isinstance(data[0], dict):
            print("First item keys:", ", ".join(sorted(data[0].keys())))
        return

    print(f"Type: {type(data).__name__}")


def save_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return path


def save_bytes(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as file:
        file.write(data)

    return path


def save_raw_file_list(series_id: str, data: Any) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / f"grid_series_{series_id}_files.json"

    return save_json(output_path, data)


def save_downloaded_file(series_id: str, file_info: dict, data: bytes) -> Path:
    file_name = file_info.get("fileName") or f"{file_info['id']}_{series_id}"
    output_path = RAW_DIR / file_name

    return save_bytes(output_path, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download one GRID end-state series payload."
    )
    parser.add_argument(
        "series_id",
        nargs="?",
        default="2589176",
        help="GRID series id to inspect."
    )
    parser.add_argument(
        "--download-id",
        default=None,
        help=(
            "Optional GRID file id to download after listing files. "
            "Examples: state-grid, events-grid-compressed."
        )
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = fetch_available_files(args.series_id)
    output_path = save_raw_file_list(args.series_id, data)

    describe_json(data)

    print()
    print("Saved:")
    print(output_path)

    files = data.get("files", [])
    if files:
        print()
        print("Available files:")
        for file_info in files:
            print(
                "- "
                f"{file_info.get('id')} | "
                f"{file_info.get('status')} | "
                f"{file_info.get('description')} | "
                f"{file_info.get('fileName')}"
            )

    if not args.download_id:
        return

    selected_file = choose_file(files, args.download_id)

    if not selected_file:
        raise ValueError(f"File id not found for this series: {args.download_id}")

    if selected_file.get("status") != "ready":
        raise ValueError(
            f"File is not ready: {args.download_id} "
            f"status={selected_file.get('status')}"
        )

    full_url = selected_file.get("fullURL")

    if not full_url:
        raise ValueError(f"File has no fullURL: {args.download_id}")

    downloaded_data = download_file(full_url)
    downloaded_path = save_downloaded_file(
        args.series_id,
        selected_file,
        downloaded_data
    )

    print()
    print("Downloaded:")
    print(downloaded_path)


if __name__ == "__main__":
    main()
