from __future__ import annotations

import json

from .models import ValueCandidate


def format_candidate(candidate: ValueCandidate) -> str:
    event = candidate.event
    best_prices = event.best_prices()
    odds_lines = "\n".join(f"- {name}: {outcome.price:.2f}" for name, outcome in best_prices.items())
    probability_lines = "\n".join(
        f"- {name}: {probability:.0%}"
        for name, probability in sorted_model_probabilities(candidate)
    )
    reason_lines = "\n".join(f"- {reason}" for reason in candidate.reasons)

    return f"""MATCH:
{event.away_team} vs {event.home_team}

BOOKMAKER ODDS:
{odds_lines}

MODEL PROBABILITIES:
{probability_lines}

EDGE DETECTED:
- {candidate.side} Edge: {candidate.edge:+.1%}

EXPECTED VALUE:
{candidate.expected_value:+.2f}

CONFIDENCE SCORE:
{candidate.confidence}/100

REASONING:
{reason_lines}

RECOMMENDATION:
{candidate.recommendation}
"""


def format_email(candidate: ValueCandidate) -> str:
    reasons = "\n".join(f"- {reason}" for reason in candidate.reasons[:3])
    return f"""SUBJECT:
Value Bet Alert - {candidate.event.away_team} vs {candidate.event.home_team}

BODY:
A potential value betting opportunity has been detected.

Match: {candidate.event.away_team} vs {candidate.event.home_team}
Recommended Side: {candidate.side}
Bookmaker Odds: {candidate.outcome.price:.2f}
Model Probability: {candidate.model_probability:.0%}
Edge: {candidate.edge:+.1%}
Confidence: {candidate.confidence}/100

Key Reasons:
{reasons}

Expected Value:
{candidate.expected_value:+.2f}

This is a probability-based analytical recommendation, not a guaranteed outcome.
"""


def candidates_to_json(candidates: list[ValueCandidate]) -> str:
    return json.dumps([candidate_to_dict(candidate) for candidate in candidates], indent=2)


def candidate_to_dict(candidate: ValueCandidate) -> dict[str, object]:
    return {
        "match": f"{candidate.event.away_team} vs {candidate.event.home_team}",
        "sport": candidate.event.sport_key,
        "side": candidate.side,
        "bookmaker": candidate.outcome.bookmaker,
        "odds": round(candidate.outcome.price, 3),
        "model_probabilities": {
            name: round(probability, 4)
            for name, probability in candidate.model_probabilities.items()
        },
        "model_probability": round(candidate.model_probability, 4),
        "implied_probability": round(candidate.implied_probability, 4),
        "edge": round(candidate.edge, 4),
        "expected_value": round(candidate.expected_value, 4),
        "confidence": candidate.confidence,
        "recommendation": candidate.recommendation,
        "reasons": list(candidate.reasons),
    }


def sorted_model_probabilities(candidate: ValueCandidate) -> list[tuple[str, float]]:
    ordered_names = candidate.event.best_prices().keys()
    return [
        (name, candidate.model_probabilities[name])
        for name in ordered_names
        if name in candidate.model_probabilities
    ]
