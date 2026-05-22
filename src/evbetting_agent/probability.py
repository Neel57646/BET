from __future__ import annotations

from .history import HistoricalModel, elo_probability
from .models import EventOdds, ProbabilityEstimate, safe_divide


def estimate_probabilities(event: EventOdds, historical: HistoricalModel) -> ProbabilityEstimate:
    home = historical.profile(event.sport_key, event.home_team)
    away = historical.profile(event.sport_key, event.away_team)
    market_outcomes = set(event.best_prices())
    reasons: dict[str, list[str]] = {name: [] for name in market_outcomes}

    if home is None or away is None:
        probabilities = no_vig_market_probabilities(event)
        for name in probabilities:
            reasons.setdefault(name, []).append("Limited historical data; model anchored to no-vig market baseline")
        return ProbabilityEstimate(probabilities=probabilities, confidence_base=35, reasons=reasons)

    home_elo_prob = elo_probability(home.elo + 55, away.elo)
    form_adjustment = clamp((home.recent_form - away.recent_form) * 0.12, -0.06, 0.06)
    venue_adjustment = clamp((home.home_win_rate - away.away_win_rate) * 0.06, -0.04, 0.04)
    margin_adjustment = clamp((home.point_margin - away.point_margin) * 0.003, -0.05, 0.05)
    home_win_no_draw = clamp(home_elo_prob + form_adjustment + venue_adjustment + margin_adjustment, 0.05, 0.95)

    draw_probability = draw_probability_for(event, historical)
    if "Draw" in market_outcomes or "Tie" in market_outcomes:
        home_probability = home_win_no_draw * (1.0 - draw_probability)
        away_probability = (1.0 - home_win_no_draw) * (1.0 - draw_probability)
    else:
        home_probability = home_win_no_draw
        away_probability = 1.0 - home_win_no_draw
        draw_probability = 0.0

    probabilities = {
        event.home_team: home_probability,
        event.away_team: away_probability,
    }
    if "Draw" in market_outcomes:
        probabilities["Draw"] = draw_probability
    if "Tie" in market_outcomes:
        probabilities["Tie"] = draw_probability

    add_reasons(reasons, event.home_team, home, away, is_home=True)
    add_reasons(reasons, event.away_team, away, home, is_home=False)
    if draw_probability:
        reasons.setdefault("Draw", []).append(f"Historical draw rate included at {draw_probability:.1%}")
        reasons.setdefault("Tie", []).append(f"Historical tie rate included at {draw_probability:.1%}")

    games_score = min(home.games, away.games, 30) / 30
    confidence_base = 45 + 30 * games_score
    return ProbabilityEstimate(probabilities=probabilities, confidence_base=confidence_base, reasons=reasons)


def no_vig_market_probabilities(event: EventOdds) -> dict[str, float]:
    best = event.best_prices()
    raw = {name: 1.0 / outcome.price for name, outcome in best.items()}
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {name: value / total for name, value in raw.items()}


def draw_probability_for(event: EventOdds, historical: HistoricalModel) -> float:
    sport_rate = historical.draw_rate(event.sport_key)
    h2h = historical.games_between(event.sport_key, event.home_team, event.away_team)
    if h2h:
        h2h_draw_rate = safe_divide(sum(1 for match in h2h if match.winner is None), len(h2h))
        sport_rate = 0.65 * sport_rate + 0.35 * h2h_draw_rate
    if event.sport_key.startswith("soccer"):
        return clamp(sport_rate or 0.26, 0.12, 0.34)
    return clamp(sport_rate, 0.0, 0.15)


def add_reasons(reasons: dict[str, list[str]], team: str, profile, opponent, is_home: bool) -> None:
    team_reasons = reasons.setdefault(team, [])
    if profile.recent_form - opponent.recent_form >= 0.12:
        team_reasons.append("Recent form advantage over last 5-10 matches")
    if is_home and profile.home_win_rate >= opponent.away_win_rate + 0.12:
        team_reasons.append("Home performance rates above opponent away baseline")
    if not is_home and profile.away_win_rate >= opponent.home_win_rate + 0.12:
        team_reasons.append("Away performance rates above opponent home baseline")
    if profile.point_margin - opponent.point_margin >= 5:
        team_reasons.append("Offensive and defensive margin profile is materially stronger")
    if profile.elo - opponent.elo >= 45:
        team_reasons.append("Elo strength rating is meaningfully higher")


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
