# EV Betting Agent

Python scaffold for a probability-first sports betting scanner. It is designed to find candidate value bets, not to predict certainties or guarantee outcomes.

The first implementation supports:

- Upcoming/live odds from The Odds API when `ODDS_API_KEY` is configured
- Local JSON odds files for testing or backfills
- Historical match CSV modeling with Elo, recent form, home/away splits, and draw-rate handling
- Recent completed scores refresh from The Odds API in live trigger mode
- Implied probability, edge, EV, confidence score, and alert filtering
- Text, JSON, and Gmail alert output
- GitHub Actions scheduled trigger, matching the crypto trigger pattern

The Odds API docs state that `/v4/sports/{sport}/odds` returns upcoming/live games with recent bookmaker odds, supports decimal odds via `oddsFormat=decimal`, and uses regions such as `au`, `us`, `uk`, and `eu`.

## Quick Start

Run the synthetic sample:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1 --sample
```

Run with your own local files:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1 --history data\sample_history.csv --odds data\sample_odds.json
```

Run live odds:

```powershell
$env:ODDS_API_KEY="your_api_key"
powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1 --live --sports aussierules_afl,basketball_nba,soccer_epl --regions au --markets h2h
```

Run live odds with recent completed scores added to the model:

```powershell
$env:ODDS_API_KEY="your_api_key"
powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1 --live --include-scores --scores-days 3 --send-email
```

If you prefer direct Python commands, either install the package with `python -m pip install -e .` or set `PYTHONPATH=src` before running `python -m evbetting_agent`.

## Email Trigger

This uses the same Gmail secret names as the crypto trigger:

```text
ALERT_EMAIL_FROM=yourgmail@gmail.com
ALERT_EMAIL_TO=yourgmail@gmail.com
GMAIL_APP_PASSWORD=your_16_character_gmail_app_password
ALERT_COOLDOWN_HOURS=24
DRY_RUN=true
```

Dry-run email test:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1 --sample --send-email
```

To send for real, set `DRY_RUN=false` and use a Gmail app password, not your normal Gmail password.

## GitHub Actions 24/7 Trigger

The workflow in `.github/workflows/sports-ev-alert.yml` runs every 15 minutes online, like the crypto trigger. It also pulls completed scores from the last 3 days before scanning odds.
If no value bet passes the threshold, it sends a no-value-bets status email at most once every 6 hours.
It also writes `docs/data/latest.json` for the static dashboard in `docs/index.html`.

Add these repository secrets in GitHub:

```text
ODDS_API_KEY=your_the_odds_api_key
ALERT_EMAIL_FROM=same_sender_as_crypto_trigger
ALERT_EMAIL_TO=same_recipient_as_crypto_trigger
GMAIL_APP_PASSWORD=same_gmail_app_password_secret
```

The workflow scans these sport keys by default:

```text
aussierules_afl
basketball_nba
soccer_epl
cricket_ipl
cricket_big_bash
cricket_international_t20
```

Tennis is tournament-specific in most odds feeds, so add active tennis keys to `WATCHED_SPORTS` when the tournament is available.

## Online Dashboard

The dashboard lives in the `docs` folder. To publish it with GitHub Pages:

1. Open repository settings.
2. Go to `Pages`.
3. Set source to `Deploy from a branch`.
4. Choose branch `main` and folder `/docs`.
5. Save.

The page will load the latest scan data from `docs/data/latest.json`.

## Data Files

Historical CSV columns:

```text
date,sport,home_team,away_team,home_score,away_score,neutral
```

Odds JSON accepts The Odds API event shape:

```json
[
  {
    "id": "event-id",
    "sport_key": "basketball_nba",
    "commence_time": "2026-05-23T09:00:00Z",
    "home_team": "Home Team",
    "away_team": "Away Team",
    "bookmakers": [
      {
        "key": "bookmaker",
        "title": "Bookmaker",
        "last_update": "2026-05-22T12:00:00Z",
        "markets": [
          {
            "key": "h2h",
            "outcomes": [
              {"name": "Home Team", "price": 2.1},
              {"name": "Away Team", "price": 1.8}
            ]
          }
        ]
      }
    ]
  }
]
```

## Alert Rules

An alert is emitted only when:

- Edge is at least `7%`
- EV is positive
- Confidence score is at least `70/100`

Default staking guidance is 1-3% of bankroll and daily exposure should be capped externally.

## Important

The included sample data is synthetic and only verifies the workflow. Live betting decisions need a valid odds feed, clean historical data, injury/suspension feeds, lineup news, weather data, and disciplined staking controls.
