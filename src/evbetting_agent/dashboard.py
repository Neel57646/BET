from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .alerts import candidate_to_dict
from .models import EventOdds, ValueCandidate


def write_dashboard_json(
    path: str | Path,
    events: list[EventOdds],
    candidates: list[ValueCandidate],
    alerts: list[ValueCandidate],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dashboard_payload(events, candidates, alerts), indent=2),
        encoding="utf-8",
    )


def dashboard_payload(
    events: list[EventOdds],
    candidates: list[ValueCandidate],
    alerts: list[ValueCandidate],
) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "value_bets" if alerts else "no_value_bets",
        "scanned_events": len(events),
        "ranked_candidates": len(candidates),
        "alert_count": len(alerts),
        "sports": sorted({event.sport_key for event in events if event.sport_key}),
        "alerts": [dashboard_candidate(candidate) for candidate in alerts],
        "watchlist": [
            dashboard_candidate(candidate)
            for candidate in candidates
            if candidate.recommendation == "Watchlist"
        ][:25],
        "ranked": [dashboard_candidate(candidate) for candidate in candidates[:50]],
    }


def dashboard_candidate(candidate: ValueCandidate) -> dict[str, object]:
    payload = candidate_to_dict(candidate)
    payload.update(
        {
            "event_id": candidate.event.event_id,
            "commence_time": candidate.event.commence_time.isoformat()
            if candidate.event.commence_time
            else None,
            "home_team": candidate.event.home_team,
            "away_team": candidate.event.away_team,
        }
    )
    return payload
