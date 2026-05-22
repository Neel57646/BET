from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_SPORTS = (
    "aussierules_afl",
    "basketball_nba",
    "cricket_ipl",
)


@dataclass(frozen=True)
class Settings:
    odds_api_key: str | None
    regions: str = "au"
    markets: str = "h2h"
    sports: tuple[str, ...] = DEFAULT_SPORTS
    min_edge: float = 0.07
    min_confidence: int = 70

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            odds_api_key=os.getenv("ODDS_API_KEY") or None,
            regions=os.getenv("ODDS_REGIONS", "au"),
            markets=os.getenv("ODDS_MARKETS", "h2h"),
            sports=parse_csv(os.getenv("WATCHED_SPORTS"), DEFAULT_SPORTS),
            min_edge=float(os.getenv("MIN_EDGE", "0.07")),
            min_confidence=int(os.getenv("MIN_CONFIDENCE", "70")),
        )


def parse_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items or default
