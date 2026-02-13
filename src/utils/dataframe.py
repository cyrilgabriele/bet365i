"""Shared DataFrame helpers for cleaning/loading match data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

WINNER_MAP = {"HOME_TEAM": "H", "AWAY_TEAM": "A", "DRAW": "D"}
ID_COLUMNS = ["id", "homeTeam.id", "awayTeam.id"]
TEAM_NAME_COLUMNS = ["homeTeam.name", "awayTeam.name"]


def _convert_to_datetime(df: pd.DataFrame, column: str) -> None:
    if column in df:
        df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)


def _convert_to_int(df: pd.DataFrame, column: str) -> None:
    if column in df:
        as_numeric = pd.to_numeric(df[column], errors="coerce")
        df[column] = as_numeric.astype("Int64")


def _strip_text(df: pd.DataFrame, column: str) -> None:
    if column in df:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", "_", regex=True)
        )


def standardize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with normalized dtypes and derived columns."""

    converted = df.copy()
    _convert_to_datetime(converted, "utcDate")
    _convert_to_datetime(converted, "lastUpdated")

    if "matchday" in converted:
        as_numeric = pd.to_numeric(converted["matchday"], errors="coerce")
        converted["matchday"] = as_numeric.astype("Int64")

    for column in ID_COLUMNS:
        _convert_to_int(converted, column)

    if "score.winner" in converted:
        mapped = converted["score.winner"].map(WINNER_MAP)
        converted["score.winner"] = mapped.fillna(converted["score.winner"])

    for column in TEAM_NAME_COLUMNS:
        _strip_text(converted, column)

    return converted


def load_cleaned_dataframe(path: Path | str) -> pd.DataFrame:
    """Load a cleaned CSV and reapply the dtype standardization helpers."""

    df = pd.read_csv(path)
    return standardize_types(df)


__all__ = ["standardize_types", "load_cleaned_dataframe"]
