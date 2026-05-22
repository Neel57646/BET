from __future__ import annotations

from datetime import datetime, timezone

from .history import HistoricalModel
from .models import EventOdds, ValueCandidate
from .probability import estimate_probabilities


def scan_events(
    events: list[EventOdds],
    historical: HistoricalModel,
    min_edge: float = 0.07,
    min_confidence: int = 70,
) -> list[ValueCandidate]:
    candidates: list[ValueCandidate] = []
    for event in events:
        estimate = estimate_probabilities(event, historical)
        for name, outcome in event.best_prices().items():
            model_probability = estimate.probabilities.get(name)
            if model_probability is None:
                continue
            implied = outcome.implied_probability
            edge = model_probability - implied
            expected_value = (model_probability * outcome.price) - 1.0
            confidence = confidence_score(event, estimate.confidence_base, edge, outcome.last_update)
            recommendation = recommendation_for(edge, expected_value, confidence, min_edge, min_confidence)
            reasons = tuple(reason_list(name, estimate.reasons, edge, event.bookmaker_count))
            candidates.append(
                ValueCandidate(
                    event=event,
                    outcome=outcome,
                    model_probabilities=estimate.probabilities,
                    model_probability=model_probability,
                    implied_probability=implied,
                    edge=edge,
                    expected_value=expected_value,
                    confidence=confidence,
                    recommendation=recommendation,
                    reasons=reasons,
                )
            )
    return sorted(candidates, key=lambda candidate: (candidate.recommendation == "Value Bet", candidate.expected_value), reverse=True)


def high_confidence_alerts(
    candidates: list[ValueCandidate],
    min_edge: float = 0.07,
    min_confidence: int = 70,
) -> list[ValueCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.edge >= min_edge and candidate.expected_value > 0 and candidate.confidence >= min_confidence
    ]


def confidence_score(
    event: EventOdds,
    confidence_base: float,
    edge: float,
    last_update: datetime | None,
) -> int:
    edge_component = max(0.0, min(18.0, (edge - 0.03) * 120))
    depth_component = min(10.0, event.bookmaker_count * 2.5)
    freshness_component = odds_freshness_score(last_update)
    confidence = confidence_base + edge_component + depth_component + freshness_component
    return int(max(0, min(100, round(confidence))))


def odds_freshness_score(last_update: datetime | None) -> float:
    if last_update is None:
        return 0.0
    now = datetime.now(timezone.utc)
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)
    age_minutes = max(0.0, (now - last_update).total_seconds() / 60)
    if age_minutes <= 30:
        return 8.0
    if age_minutes <= 180:
        return 4.0
    return 0.0


def recommendation_for(edge: float, expected_value: float, confidence: int, min_edge: float, min_confidence: int) -> str:
    if edge >= min_edge and expected_value > 0 and confidence >= min_confidence:
        return "Value Bet"
    if expected_value > 0 and edge >= min_edge * 0.6:
        return "Watchlist"
    return "No Bet"


def reason_list(name: str, reasons: dict[str, list[str]], edge: float, bookmaker_count: int) -> list[str]:
    output = list(reasons.get(name, []))
    if edge > 0:
        output.append("Model probability is above the best available bookmaker implied probability")
    if bookmaker_count >= 3:
        output.append("Multiple bookmakers available for price comparison")
    if not output:
        output.append("No durable statistical edge detected at current price")
    return output[:5]
