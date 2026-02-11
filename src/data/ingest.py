"""Utilities for downloading football-data.org assets.

The first iteration only targets Premier League matches via the v4 REST API.
Actual download calls are encapsulated so that consumers can enforce rate
limits and persist files into ``data/raw`` in a reproducible fashion.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping

import requests
from dotenv import load_dotenv


API_BASE_URL = "https://api.football-data.org/v4"
# API limit: default 10 requests/minute, so wait slightly >6s between calls.
MIN_REQUEST_INTERVAL_SECONDS = 6.2
DEFAULT_COMPETITION_CODE = "PL"
RAW_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "football_data"


def load_api_token(env_var: str = "FOOTBALL_DATA_API_TOKEN") -> str:
    """Read the API token from the environment and fail early if missing."""

    token = os.getenv(env_var)
    if not token:
        raise RuntimeError(
            f"Set the {env_var} environment variable with your football-data.org token."
        )
    return token


class FootballDataClient:
    """Thin HTTP client with naive rate limiting to respect API quotas."""

    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = API_BASE_URL,
        min_interval_seconds: float = MIN_REQUEST_INTERVAL_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers["X-Auth-Token"] = api_token
        self.min_interval_seconds = min_interval_seconds
        self._last_request_ts: float | None = None

    def get(self, endpoint: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Issue a GET request while respecting the built-in delay."""

        now = time.time()
        if self._last_request_ts is not None:
            elapsed = now - self._last_request_ts
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params, timeout=30)
        self._last_request_ts = time.time()
        response.raise_for_status()
        return response.json()


@dataclass(slots=True)
class PremierLeagueFetchParams:
    """Filter options supported by football-data for Premier League pulls."""

    season: int
    status: str = "FINISHED"
    date_from: str | None = None  # YYYY-MM-DD, inclusive
    date_to: str | None = None  # YYYY-MM-DD, inclusive
    competition_code: str = DEFAULT_COMPETITION_CODE

    def to_query(self) -> dict[str, Any]:
        """Translate the dataclass into the query params accepted by the API."""

        query: dict[str, Any] = {"season": self.season, "status": self.status}
        if self.date_from:
            query["dateFrom"] = self.date_from
        if self.date_to:
            query["dateTo"] = self.date_to
        return query


class PremierLeagueFetcher:
    """Download helper dedicated to Premier League matches."""

    def __init__(
        self,
        client: FootballDataClient,
        *,
        output_dir: Path | None = None,
    ) -> None:
        self.client = client
        self.output_dir = output_dir or RAW_DATA_ROOT
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, params: PremierLeagueFetchParams, *, save: bool = True) -> Mapping[str, Any]:
        """Fetch match listings for the requested season and optionally persist JSON."""

        endpoint = f"competitions/{params.competition_code}/matches"
        payload = self.client.get(endpoint, params=params.to_query())

        if save:
            out_path = self._build_output_path(params)
            out_path.write_text(json.dumps(payload, indent=2))
        return payload

    def _build_output_path(self, params: PremierLeagueFetchParams) -> Path:
        suffix = params.status.lower()
        filename = f"premier_league_{params.season}_{suffix}.json"
        return self.output_dir / filename


def build_premier_league_fetcher(*, token_env_var: str = "FOOTBALL_DATA_API_TOKEN") -> PremierLeagueFetcher:
    """Factory that hides token loading for quick scripts/CLI usage."""

    token = load_api_token(env_var=token_env_var)
    client = FootballDataClient(api_token=token)
    return PremierLeagueFetcher(client)


def describe_filters() -> str:
    """Return a short description of supported filters for documentation/CLI help."""

    return (
        "Filters available: season (int, required), status (e.g. FINISHED, SCHEDULED), "
        "dateFrom/dateTo (YYYY-MM-DD). The client is scoped to competitions/PL only."
    )


__all__ = [
    "PremierLeagueFetcher",
    "PremierLeagueFetchParams",
    "FootballDataClient",
    "build_premier_league_fetcher",
    "describe_filters",
]
