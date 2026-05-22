from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .models import ValueCandidate


def load_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_state(path: str | Path, state: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def should_send(candidate: ValueCandidate, state: dict[str, Any]) -> bool:
    cooldown_hours = int(os.getenv("ALERT_COOLDOWN_HOURS", "24"))
    previous = state.get(alert_key(candidate))
    if not previous:
        return True

    confidence_changed = abs(int(previous.get("confidence", 0)) - candidate.confidence) >= 10
    edge_changed = abs(float(previous.get("edge", 0.0)) - candidate.edge) >= 0.05
    if confidence_changed or edge_changed:
        return True

    now = int(time.time())
    return now - int(previous.get("sent_at", 0)) >= cooldown_hours * 3600


def remember(candidate: ValueCandidate, state: dict[str, Any]) -> None:
    state[alert_key(candidate)] = {
        "sent_at": int(time.time()),
        "match": f"{candidate.event.away_team} vs {candidate.event.home_team}",
        "side": candidate.side,
        "bookmaker": candidate.outcome.bookmaker,
        "odds": candidate.outcome.price,
        "edge": candidate.edge,
        "expected_value": candidate.expected_value,
        "confidence": candidate.confidence,
    }


def alert_key(candidate: ValueCandidate) -> str:
    event_id = candidate.event.event_id or f"{candidate.event.sport_key}:{candidate.event.away_team}:{candidate.event.home_team}"
    return f"{event_id}:{candidate.side}:{candidate.recommendation}"
