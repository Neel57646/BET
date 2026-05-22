import unittest

from evbetting_agent.ev import high_confidence_alerts, scan_events
from evbetting_agent.history import HistoricalModel
from evbetting_agent.models import EventOdds, HistoricalMatch, OutcomeOdds


class EVMathTests(unittest.TestCase):
    def test_decimal_implied_probability(self):
        outcome = OutcomeOdds(name="Team A", price=2.5, bookmaker="Book")
        self.assertAlmostEqual(outcome.implied_probability, 0.4)

    def test_positive_ev_formula(self):
        ev = (0.55 * 2.1) - 1
        self.assertAlmostEqual(ev, 0.155)

    def test_alert_filtering_requires_thresholds(self):
        history = HistoricalModel(
            [
                HistoricalMatch(
                    date=__import__("datetime").datetime.fromisoformat(f"2026-01-{day:02d}"),
                    sport="basketball_nba",
                    home_team="Home",
                    away_team="Away",
                    home_score=110 + day,
                    away_score=95,
                )
                for day in range(1, 16)
            ]
        )
        event = EventOdds(
            event_id="x",
            sport_key="basketball_nba",
            commence_time=None,
            home_team="Home",
            away_team="Away",
            outcomes=(
                OutcomeOdds(name="Home", price=2.05, bookmaker="Book A"),
                OutcomeOdds(name="Away", price=1.85, bookmaker="Book A"),
                OutcomeOdds(name="Home", price=2.08, bookmaker="Book B"),
                OutcomeOdds(name="Away", price=1.82, bookmaker="Book B"),
            ),
        )
        candidates = scan_events([event], history, min_edge=0.07, min_confidence=70)
        alerts = high_confidence_alerts(candidates, min_edge=0.07, min_confidence=70)
        self.assertTrue(any(candidate.side == "Home" for candidate in alerts))


if __name__ == "__main__":
    unittest.main()
