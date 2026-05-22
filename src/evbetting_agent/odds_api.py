from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import EventOdds, HistoricalMatch, OutcomeOdds


API_BASE = "https://api.the-odds-api.com"


class OddsAPIError(RuntimeError):
    pass


class TheOddsAPIClient:
    def __init__(self, api_key: str, base_url: str = API_BASE, timeout: int = 20) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_odds(
        self,
        sport: str,
        regions: str = "au",
        markets: str = "h2h",
        odds_format: str = "decimal",
    ) -> list[EventOdds]:
        params = urlencode(
            {
                "apiKey": self.api_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
                "dateFormat": "iso",
            }
        )
        payload = self._get_json(f"/v4/sports/{sport}/odds/?{params}")
        return parse_events(payload)

    def fetch_sports(self, include_all: bool = False) -> list[dict[str, Any]]:
        params = {"apiKey": self.api_key}
        if include_all:
            params["all"] = "true"
        payload = self._get_json(f"/v4/sports/?{urlencode(params)}")
        if not isinstance(payload, list):
            raise OddsAPIError("Unexpected sports response")
        return payload

    def fetch_scores(self, sport: str, days_from: int | None = 3) -> list[HistoricalMatch]:
        params: dict[str, str | int] = {
            "apiKey": self.api_key,
            "dateFormat": "iso",
        }
        if days_from is not None:
            params["daysFrom"] = max(1, min(3, days_from))
        payload = self._get_json(f"/v4/sports/{sport}/scores/?{urlencode(params)}")
        return parse_score_events(payload, sport)

    def _get_json(self, path: str) -> Any:
        request = Request(f"{self.base_url}{path}", headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network dependent
            raise OddsAPIError(str(exc)) from exc
        return json.loads(body)


def load_odds_file(path: str | Path) -> list[EventOdds]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_events(raw)


def parse_events(payload: Any) -> list[EventOdds]:
    if not isinstance(payload, list):
        raise OddsAPIError("Odds payload must be a list of events")

    events: list[EventOdds] = []
    for item in payload:
        outcomes: list[OutcomeOdds] = []
        for bookmaker in item.get("bookmakers", []):
            bookmaker_name = bookmaker.get("title") or bookmaker.get("key") or "Unknown"
            last_update = parse_datetime(bookmaker.get("last_update"))
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    price = outcome.get("price")
                    if not name or price is None:
                        continue
                    outcomes.append(
                        OutcomeOdds(
                            name=str(name),
                            price=float(price),
                            bookmaker=bookmaker_name,
                            last_update=last_update,
                        )
                    )

        events.append(
            EventOdds(
                event_id=str(item.get("id", "")),
                sport_key=str(item.get("sport_key", "")),
                commence_time=parse_datetime(item.get("commence_time")),
                home_team=str(item.get("home_team", "")),
                away_team=str(item.get("away_team", "")),
                outcomes=tuple(outcomes),
            )
        )
    return events


def parse_score_events(payload: Any, sport: str) -> list[HistoricalMatch]:
    if not isinstance(payload, list):
        raise OddsAPIError("Scores payload must be a list of events")

    matches: list[HistoricalMatch] = []
    for item in payload:
        if not item.get("completed"):
            continue

        home_team = str(item.get("home_team", ""))
        away_team = str(item.get("away_team", ""))
        scores: dict[str, float] = {}
        for score in item.get("scores") or []:
            if not score.get("name") or score.get("score") is None:
                continue
            try:
                scores[str(score.get("name"))] = parse_score_value(score.get("score"))
            except ValueError:
                continue
        if home_team not in scores or away_team not in scores:
            continue

        matches.append(
            HistoricalMatch(
                date=parse_datetime(item.get("commence_time")) or datetime.min,
                sport=str(item.get("sport_key") or sport),
                home_team=home_team,
                away_team=away_team,
                home_score=scores[home_team],
                away_score=scores[away_team],
                neutral=False,
            )
        )
    return matches


def parse_score_value(value: Any) -> float:
    text = str(value).strip()
    if not text:
        raise ValueError("Missing score value")
    number = []
    for char in text:
        if char.isdigit() or char in {".", "-"}:
            number.append(char)
        elif number:
            break
    if not number:
        raise ValueError(f"Cannot parse score value: {value!r}")
    return float("".join(number))


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    return datetime.fromisoformat(value)
