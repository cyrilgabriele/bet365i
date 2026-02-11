"""Data modules (ingest, cleaning, feature prep)."""

from .ingest import (
    FootballDataClient,
    PremierLeagueFetchParams,
    PremierLeagueFetcher,
    build_premier_league_fetcher,
    describe_filters,
)

__all__ = [
    "FootballDataClient",
    "PremierLeagueFetchParams",
    "PremierLeagueFetcher",
    "build_premier_league_fetcher",
    "describe_filters",
]

