"""Orchestrator for ingesting, cleaning, and featurizing football-data assets."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from data import PremierLeagueFetchParams, build_premier_league_fetcher
from data.clean import clean_dataframe, infer_output_path
from data.features import load_features_from_cleaned, one_hot_encode_text_columns

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES_DATA_DIR = PROJECT_ROOT / "data" / "features" / "football_data"

DATASETS = [
    {"season": 2023, "status": "FINISHED", "competition": "PL"},
    {"season": 2024, "status": "FINISHED", "competition": "PL"},
    {"season": 2025, "status": "FINISHED", "competition": "PL"},
]


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


def ingest_dataset(fetcher, *, season: int, status: str, competition: str) -> Path:
    params = PremierLeagueFetchParams(
        season=season,
        status=status,
        competition_code=competition,
    )
    payload = fetcher.fetch(params, save=False)
    matches = payload.get("matches", []) if isinstance(payload, Mapping) else []
    csv_path = build_csv_path(fetcher.output_dir, params)
    matches_to_csv(matches, csv_path)
    print(
        f"Ingested {len(matches)} matches for {competition} {season}"
        f" (status={status}) -> {csv_path}"
    )
    return csv_path


def clean_dataset(raw_csv: Path) -> Path:
    df = pd.read_csv(raw_csv)
    cleaned, dropped = clean_dataframe(df)
    output_path = infer_output_path(raw_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    print(f"  Cleaned dataset ({len(dropped)} cols dropped) -> {output_path}")
    return output_path


def build_feature_matrix(cleaned_csv: Path) -> Path:
    FEATURES_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = load_features_from_cleaned(cleaned_csv.name)
    encoded_df, column_map = one_hot_encode_text_columns(df)
    feature_name = cleaned_csv.name.replace("cleaned_", "features_", 1)
    feature_path = FEATURES_DATA_DIR / feature_name
    encoded_df.to_csv(feature_path, index=False)
    print(
        f"  Built feature matrix with {encoded_df.shape[1]} columns -> {feature_path}"
    )
    print(f"    Encoded columns: {', '.join(column_map.keys()) or 'None'}")
    return feature_path


def run_pipeline() -> None:
    load_dotenv()
    fetcher = build_premier_league_fetcher()

    for dataset in DATASETS:
        raw_csv = ingest_dataset(
            fetcher,
            season=dataset["season"],
            status=dataset["status"],
            competition=dataset["competition"],
        )
        cleaned_csv = clean_dataset(raw_csv)
        build_feature_matrix(cleaned_csv)

    print("Pipeline completed for all datasets.")


def main() -> None:  # pragma: no cover - script entry point
    run_pipeline()


if __name__ == "__main__":
    main()
