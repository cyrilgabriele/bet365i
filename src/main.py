"""CLI utilities for requesting football-data.org assets and storing them as CSV."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from data import (
    PremierLeagueFetchParams,
    build_premier_league_fetcher,
    describe_filters,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Request Premier League match listings via football-data.org API.\n"
            f"{describe_filters()}"
        )
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season start year (e.g. 2023 for the 2023-24 campaign).",
    )
    parser.add_argument(
        "--status",
        default="FINISHED",
        help="Match status filter accepted by football-data.org (default: FINISHED).",
    )
    parser.add_argument(
        "--date-from",
        dest="date_from",
        help="Lower bound date (YYYY-MM-DD, inclusive).",
    )
    parser.add_argument(
        "--date-to",
        dest="date_to",
        help="Upper bound date (YYYY-MM-DD, inclusive).",
    )
    parser.add_argument(
        "--competition",
        default="PL",
        help="Override the competition code if needed (default: PL).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writing to disk and only print the API response summary.",
    )
    return parser


def flatten_json(value: Any, *, prefix: str = "") -> dict[str, Any]:
    """Recursively flatten nested match payloads using dot notation keys."""

    if isinstance(value, Mapping):
        items: dict[str, Any] = {}
        for key, nested in value.items():
            nested_prefix = f"{prefix}.{key}" if prefix else key
            items.update(flatten_json(nested, prefix=nested_prefix))
        return items
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        serialised = json.dumps(value, ensure_ascii=False)
        return {prefix: serialised} if prefix else {}
    return {prefix: value} if prefix else {}


def matches_to_csv(matches: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    """Convert a list of match dictionaries into a flattened CSV table."""

    rows = [flatten_json(match) for match in matches]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        output_path.write_text("", encoding="utf-8") 
        return

    # Preserve first-seen order to keep column ordering stable across runs.
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def build_csv_path(output_dir: Path, params: PremierLeagueFetchParams) -> Path:
    suffix = params.status.lower()
    competition = params.competition_code.lower()
    filename = f"{competition}_{params.season}_{suffix}.csv"
    return output_dir / filename


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    load_dotenv()
    fetcher = build_premier_league_fetcher()
    params = PremierLeagueFetchParams(
        season=args.season,
        status=args.status,
        date_from=args.date_from,
        date_to=args.date_to,
        competition_code=args.competition,
    )
    payload = fetcher.fetch(params, save=False)

    matches = payload.get("matches", []) if isinstance(payload, Mapping) else []
    print(
        "Fetched"
        f" {len(matches)} matches for competition {params.competition_code}"
        f" season {params.season} (status={params.status})."
    )
    if args.dry_run:
        print("Dry-run enabled, payload not written to disk.")
    else:
        csv_path = build_csv_path(fetcher.output_dir, params)
        matches_to_csv(matches, csv_path)
        print(f"Saved flattened CSV to {csv_path}")


if __name__ == "__main__":
    main()
