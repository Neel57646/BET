from __future__ import annotations

import argparse
import os
from pathlib import Path

from .alerts import candidates_to_json, format_candidate, format_email
from .config import Settings, parse_csv
from .email_delivery import build_alert_email, build_no_alert_email, send_email
from .env import load_env
from .ev import high_confidence_alerts, scan_events
from .history import HistoricalModel, load_history_csv
from .odds_api import OddsAPIError, TheOddsAPIClient, load_odds_file
from .state import load_state, remember, remember_empty_report, save_state, should_send, should_send_empty_report


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
    parser.add_argument("--include-scores", action="store_true", help="Use recent completed scores to refresh the model in live mode.")
    parser.add_argument("--scores-days", type=int, default=3, help="Completed score lookback, 1-3 days.")
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

    base_history = load_history_csv(history_path)
    client = TheOddsAPIClient(settings.odds_api_key) if args.live and settings.odds_api_key else None
    if args.include_scores and args.live and client:
        base_history = extend_history_with_scores(base_history, client, args, settings)
    historical = HistoricalModel(base_history)
    events = fetch_events(args, settings, odds_path, client)
    candidates = scan_events(events, historical, min_edge=args.min_edge, min_confidence=args.min_confidence)
    selected = candidates if args.all else high_confidence_alerts(candidates, args.min_edge, args.min_confidence)

    if args.send_email:
        return send_alerts(selected, args.state, scanned_events=len(events), ranked_candidates=len(candidates))

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


def send_alerts(candidates, state_path: str, scanned_events: int = 0, ranked_candidates: int = 0) -> int:
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    state = load_state(state_path)
    to_send = [candidate for candidate in candidates if should_send(candidate, state)]

    if not to_send:
        send_empty = os.getenv("SEND_EMPTY_REPORT", "false").lower() == "true"
        if send_empty and should_send_empty_report(state):
            message = build_no_alert_email(scanned_events, ranked_candidates)
            print(message)
            if not dry_run:
                send_email(message)
            remember_empty_report(state, scanned_events, ranked_candidates)
            save_state(state_path, state)
            print("Done. One no-value-bets sports EV summary email sent.")
            return 0
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


def extend_history_with_scores(matches, client: TheOddsAPIClient, args: argparse.Namespace, settings: Settings):
    combined = list(matches)
    seen = {history_key(match) for match in combined}
    for sport in parse_csv(args.sports, settings.sports):
        try:
            recent = client.fetch_scores(sport=sport, days_from=args.scores_days)
        except OddsAPIError as exc:
            print(f"{sport}: scores skipped ({exc})")
            continue
        added = 0
        for match in recent:
            key = history_key(match)
            if key in seen:
                continue
            combined.append(match)
            seen.add(key)
            added += 1
        print(f"{sport}: added {added} recent completed scores")
    return combined


def history_key(match) -> tuple[str, str, str, str]:
    return (
        match.sport,
        match.date.date().isoformat(),
        match.home_team,
        match.away_team,
    )


def fetch_events(args: argparse.Namespace, settings: Settings, odds_path: Path, client: TheOddsAPIClient | None = None):
    if not args.live:
        return load_odds_file(odds_path)

    if not settings.odds_api_key:
        raise SystemExit("ODDS_API_KEY is required for --live mode.")

    client = client or TheOddsAPIClient(settings.odds_api_key)
    events = []
    for sport in parse_csv(args.sports, settings.sports):
        try:
            events.extend(client.fetch_odds(sport=sport, regions=args.regions, markets=args.markets))
        except OddsAPIError as exc:
            print(f"{sport}: odds skipped ({exc})")
    return events
