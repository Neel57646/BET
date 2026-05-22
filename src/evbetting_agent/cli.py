from __future__ import annotations

import argparse
import os
from pathlib import Path

from .alerts import candidates_to_json, format_candidate, format_email
from .config import Settings, parse_csv
from .email_delivery import build_alert_email, send_email
from .env import load_env
from .ev import high_confidence_alerts, scan_events
from .history import HistoricalModel, load_history_csv
from .odds_api import TheOddsAPIClient, load_odds_file
from .state import load_state, remember, save_state, should_send


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_HISTORY = ROOT / "data" / "sample_history.csv"
SAMPLE_ODDS = ROOT / "data" / "sample_odds.json"


def main(argv: list[str] | None = None) -> int:
    load_env()
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="Scan sports odds for positive-EV betting opportunities.")
    parser.add_argument("--sample", action="store_true", help="Use synthetic sample history and odds files.")
    parser.add_argument("--history", default=str(SAMPLE_HISTORY), help="Historical match CSV path.")
    parser.add_argument("--odds", default=str(SAMPLE_ODDS), help="Local odds JSON path.")
    parser.add_argument("--live", action="store_true", help="Fetch live/upcoming odds from The Odds API.")
    parser.add_argument("--sports", default=",".join(settings.sports), help="Comma-separated The Odds API sport keys.")
    parser.add_argument("--regions", default=settings.regions, help="Bookmaker regions, for example au,us,uk,eu.")
    parser.add_argument("--markets", default=settings.markets, help="Markets to request, default h2h.")
    parser.add_argument("--min-edge", type=float, default=settings.min_edge, help="Minimum edge threshold, default 0.07.")
    parser.add_argument("--min-confidence", type=int, default=settings.min_confidence, help="Minimum confidence threshold.")
    parser.add_argument("--all", action="store_true", help="Print all ranked candidates instead of alerts only.")
    parser.add_argument("--email", action="store_true", help="Print email alert templates for alerts.")
    parser.add_argument("--send-email", action="store_true", help="Send one Gmail summary email for eligible alerts.")
    parser.add_argument("--state", default="alert_state.json", help="Cooldown state path for sent alerts.")
    parser.add_argument("--json", action="store_true", help="Output JSON.")
    args = parser.parse_args(argv)

    history_path = SAMPLE_HISTORY if args.sample else Path(args.history)
    odds_path = SAMPLE_ODDS if args.sample else Path(args.odds)

    historical = HistoricalModel(load_history_csv(history_path))
    events = fetch_events(args, settings, odds_path)
    candidates = scan_events(events, historical, min_edge=args.min_edge, min_confidence=args.min_confidence)
    selected = candidates if args.all else high_confidence_alerts(candidates, args.min_edge, args.min_confidence)

    if args.send_email:
        return send_alerts(selected, args.state)

    if args.json:
        print(candidates_to_json(selected))
        return 0

    if not selected:
        print("No high-confidence value bets found at the configured thresholds.")
        print(f"Scanned events: {len(events)}")
        print(f"Ranked candidates: {len(candidates)}")
        print("Recommendation: No Bet")
        return 0

    formatter = format_email if args.email else format_candidate
    print("\n---\n".join(formatter(candidate) for candidate in selected))
    return 0


def send_alerts(candidates, state_path: str) -> int:
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    state = load_state(state_path)
    to_send = [candidate for candidate in candidates if should_send(candidate, state)]

    if not to_send:
        print("Done. No new sports EV alerts to send.")
        return 0

    message = build_alert_email(to_send)
    print(message)
    if not dry_run:
        send_email(message)
    for candidate in to_send:
        remember(candidate, state)
    save_state(state_path, state)
    print(f"Done. One sports EV summary email {'printed' if dry_run else 'sent'} with {len(to_send)} alerts.")
    return 0


def fetch_events(args: argparse.Namespace, settings: Settings, odds_path: Path):
    if not args.live:
        return load_odds_file(odds_path)

    if not settings.odds_api_key:
        raise SystemExit("ODDS_API_KEY is required for --live mode.")

    client = TheOddsAPIClient(settings.odds_api_key)
    events = []
    for sport in parse_csv(args.sports, settings.sports):
        events.extend(client.fetch_odds(sport=sport, regions=args.regions, markets=args.markets))
    return events
