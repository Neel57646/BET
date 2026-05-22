from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .models import HistoricalMatch, TeamProfile


def load_history_csv(path: str | Path) -> list[HistoricalMatch]:
    matches: list[HistoricalMatch] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            matches.append(
                HistoricalMatch(
                    date=datetime.fromisoformat(row["date"]),
                    sport=row["sport"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    home_score=float(row["home_score"]),
                    away_score=float(row["away_score"]),
                    neutral=row.get("neutral", "").lower() in {"1", "true", "yes"},
                )
            )
    return sorted(matches, key=lambda match: match.date)


class HistoricalModel:
    def __init__(self, matches: list[HistoricalMatch]) -> None:
        self.matches = matches
        self.profiles: dict[tuple[str, str], TeamProfile] = {}
        self.sport_draw_rates: dict[str, float] = {}
        self._build()

    def profile(self, sport: str, team: str) -> TeamProfile | None:
        return self.profiles.get((sport, team))

    def draw_rate(self, sport: str) -> float:
        return self.sport_draw_rates.get(sport, 0.0)

    def games_between(self, sport: str, team_a: str, team_b: str) -> list[HistoricalMatch]:
        names = {team_a, team_b}
        return [
            match
            for match in self.matches
            if match.sport == sport and {match.home_team, match.away_team} == names
        ]

    def _build(self) -> None:
        profiles: dict[tuple[str, str], TeamProfile] = {}
        draws_by_sport: dict[str, int] = defaultdict(int)
        games_by_sport: dict[str, int] = defaultdict(int)

        for match in self.matches:
            home = profiles.setdefault((match.sport, match.home_team), TeamProfile(match.home_team))
            away = profiles.setdefault((match.sport, match.away_team), TeamProfile(match.away_team))

            expected_home = elo_probability(home.elo + (0 if match.neutral else 55), away.elo)
            home_result = result_score(match.home_score, match.away_score)
            elo_delta = 24 * (home_result - expected_home)
            home.elo += elo_delta
            away.elo -= elo_delta

            update_profile(home, match.home_score, match.away_score, is_home=True)
            update_profile(away, match.away_score, match.home_score, is_home=False)

            if match.home_score == match.away_score:
                draws_by_sport[match.sport] += 1
            games_by_sport[match.sport] += 1

        self.profiles = profiles
        self.sport_draw_rates = {
            sport: draws_by_sport[sport] / games
            for sport, games in games_by_sport.items()
            if games > 0
        }


def update_profile(profile: TeamProfile, points_for: float, points_against: float, is_home: bool) -> None:
    profile.games += 1
    profile.points_for += points_for
    profile.points_against += points_against

    if points_for > points_against:
        profile.wins += 1
        profile.recent_results.append(1.0)
        if is_home:
            profile.home_wins += 1
        else:
            profile.away_wins += 1
    elif points_for == points_against:
        profile.draws += 1
        profile.recent_results.append(0.5)
    else:
        profile.recent_results.append(0.0)

    if is_home:
        profile.home_games += 1
    else:
        profile.away_games += 1


def elo_probability(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))


def result_score(score_a: float, score_b: float) -> float:
    if score_a > score_b:
        return 1.0
    if score_a < score_b:
        return 0.0
    return 0.5
