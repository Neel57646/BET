from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class OutcomeOdds:
    name: str
    price: float
    bookmaker: str
    last_update: datetime | None = None

    @property
    def implied_probability(self) -> float:
        return 1.0 / self.price


@dataclass(frozen=True)
class EventOdds:
    event_id: str
    sport_key: str
    commence_time: datetime | None
    home_team: str
    away_team: str
    outcomes: tuple[OutcomeOdds, ...]

    @property
    def matchup(self) -> str:
        return f"{self.away_team} vs {self.home_team}"

    @property
    def bookmaker_count(self) -> int:
        return len({outcome.bookmaker for outcome in self.outcomes})

    def best_prices(self) -> dict[str, OutcomeOdds]:
        best: dict[str, OutcomeOdds] = {}
        for outcome in self.outcomes:
            if outcome.price <= 1:
                continue
            current = best.get(outcome.name)
            if current is None or outcome.price > current.price:
                best[outcome.name] = outcome
        return best


@dataclass(frozen=True)
class HistoricalMatch:
    date: datetime
    sport: str
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    neutral: bool = False

    @property
    def winner(self) -> str | None:
        if self.home_score > self.away_score:
            return self.home_team
        if self.away_score > self.home_score:
            return self.away_team
        return None


@dataclass
class TeamProfile:
    team: str
    games: int = 0
    wins: int = 0
    draws: int = 0
    home_games: int = 0
    home_wins: int = 0
    away_games: int = 0
    away_wins: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    recent_results: list[float] = field(default_factory=list)
    elo: float = 1500.0

    @property
    def win_rate(self) -> float:
        return safe_divide(self.wins + 0.5 * self.draws, self.games, default=0.5)

    @property
    def recent_form(self) -> float:
        if not self.recent_results:
            return 0.5
        return sum(self.recent_results[-10:]) / len(self.recent_results[-10:])

    @property
    def home_win_rate(self) -> float:
        return safe_divide(self.home_wins, self.home_games, default=0.5)

    @property
    def away_win_rate(self) -> float:
        return safe_divide(self.away_wins, self.away_games, default=0.5)

    @property
    def point_margin(self) -> float:
        return safe_divide(self.points_for - self.points_against, self.games, default=0.0)


@dataclass(frozen=True)
class ProbabilityEstimate:
    probabilities: dict[str, float]
    confidence_base: float
    reasons: dict[str, list[str]]


@dataclass(frozen=True)
class ValueCandidate:
    event: EventOdds
    outcome: OutcomeOdds
    model_probabilities: dict[str, float]
    model_probability: float
    implied_probability: float
    edge: float
    expected_value: float
    confidence: int
    recommendation: str
    reasons: tuple[str, ...]

    @property
    def side(self) -> str:
        return self.outcome.name

    @property
    def generated_at(self) -> datetime:
        return datetime.now(timezone.utc)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator
