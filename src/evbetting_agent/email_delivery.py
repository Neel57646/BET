from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

from .models import ValueCandidate


def build_alert_email(candidates: list[ValueCandidate]) -> EmailMessage:
    sender = os.environ["ALERT_EMAIL_FROM"]
    recipient = os.environ["ALERT_EMAIL_TO"]
    subject = f"Sports EV Alert Summary - {len(candidates)} Value Bets"

    cards = "\n".join(candidate_card(candidate) for candidate in candidates)
    html_body = f"""
<html>
<body style="margin: 0; padding: 12px; background-color: #f6f6f6;">
  <div style="max-width: 680px; margin: auto;">
    <h1 style="font-family: Arial, sans-serif; font-size: 22px; margin-bottom: 8px;">
      Sports EV Alert Summary
    </h1>
    <p style="font-family: Arial, sans-serif; font-size: 14px;">
      Total value bets: <strong>{len(candidates)}</strong><br>
      Alert rule: edge at least 7%, positive EV, confidence at least 70/100.
    </p>
    {cards}
    <p style="font-family: Arial, sans-serif; font-size: 12px; color: #666;">
      This is probability-based betting analysis, not a guaranteed outcome.<br>
      Suggested staking: 1-3% bankroll only, with daily exposure limits.
    </p>
  </div>
</body>
</html>
"""

    plain_body = "Sports EV Alert Summary\n\n"
    plain_body += f"Total value bets: {len(candidates)}\n"
    plain_body += "Alert rule: edge >= 7%, EV positive, confidence >= 70/100.\n\n"
    for candidate in candidates:
        plain_body += f"{candidate.event.away_team} vs {candidate.event.home_team}\n"
        plain_body += f"Recommended Side: {candidate.side}\n"
        plain_body += f"Bookmaker Odds: {candidate.outcome.price:.2f} ({candidate.outcome.bookmaker})\n"
        plain_body += f"Model Probability: {candidate.model_probability:.0%}\n"
        plain_body += f"Implied Probability: {candidate.implied_probability:.0%}\n"
        plain_body += f"Edge: {candidate.edge:+.1%}\n"
        plain_body += f"Expected Value: {candidate.expected_value:+.2f}\n"
        plain_body += f"Confidence: {candidate.confidence}/100\n"
        plain_body += "Key Reasons:\n"
        for reason in candidate.reasons[:3]:
            plain_body += f"  - {reason}\n"
        plain_body += "\n"

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")
    return message


def build_no_alert_email(scanned_events: int, ranked_candidates: int) -> EmailMessage:
    sender = os.environ["ALERT_EMAIL_FROM"]
    recipient = os.environ["ALERT_EMAIL_TO"]
    subject = "Sports EV Scan Summary - No Value Bets"

    plain_body = f"""Sports EV Scan Summary

No high-confidence value bets were found in this run.

Scanned events: {scanned_events}
Ranked candidates: {ranked_candidates}
Alert rule: edge >= 7%, EV positive, confidence >= 70/100.

This means the scanner ran, but no opportunity passed the alert threshold.
"""
    html_body = f"""
<html>
<body style="margin: 0; padding: 12px; background-color: #f6f6f6;">
  <div style="max-width: 680px; margin: auto; font-family: Arial, sans-serif;">
    <h1 style="font-size: 22px; margin-bottom: 8px;">Sports EV Scan Summary</h1>
    <p>No high-confidence value bets were found in this run.</p>
    <p>
      <strong>Scanned events:</strong> {scanned_events}<br>
      <strong>Ranked candidates:</strong> {ranked_candidates}<br>
      <strong>Alert rule:</strong> edge at least 7%, positive EV, confidence at least 70/100.
    </p>
    <p style="font-size: 12px; color: #666;">
      This means the scanner ran, but no opportunity passed the alert threshold.
    </p>
  </div>
</body>
</html>
"""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")
    return message


def send_email(message: EmailMessage) -> None:
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(os.environ["ALERT_EMAIL_FROM"], password)
        server.send_message(message)


def candidate_card(candidate: ValueCandidate) -> str:
    reasons = "".join(f"<li>{reason}</li>" for reason in candidate.reasons[:4])
    probabilities = "".join(
        f"<li>{name}: {probability:.0%}</li>"
        for name, probability in candidate.model_probabilities.items()
    )
    return f"""
<div style="
border: 1px solid #ddd;
border-radius: 12px;
padding: 14px;
margin-bottom: 14px;
font-family: Arial, sans-serif;
background-color: #ffffff;
">
  <h2 style="margin: 0 0 8px 0; font-size: 20px;">
    {candidate.event.away_team} vs {candidate.event.home_team}
  </h2>
  <p style="margin: 4px 0;"><strong>Recommended Side:</strong> {candidate.side}</p>
  <p style="margin: 4px 0;"><strong>Best Odds:</strong> {candidate.outcome.price:.2f} at {candidate.outcome.bookmaker}</p>
  <p style="margin: 4px 0;"><strong>Model Probability:</strong> {candidate.model_probability:.0%}</p>
  <p style="margin: 4px 0;"><strong>Implied Probability:</strong> {candidate.implied_probability:.0%}</p>
  <p style="margin: 4px 0;"><strong>Edge:</strong> {candidate.edge:+.1%}</p>
  <p style="margin: 4px 0;"><strong>Expected Value:</strong> {candidate.expected_value:+.2f}</p>
  <p style="margin: 4px 0;"><strong>Confidence:</strong> {candidate.confidence}/100</p>
  <p style="margin: 10px 0 4px 0;"><strong>Model Probabilities:</strong></p>
  <ul style="margin-top: 4px; padding-left: 20px;">{probabilities}</ul>
  <p style="margin: 10px 0 4px 0;"><strong>Reasons:</strong></p>
  <ul style="margin-top: 4px; padding-left: 20px;">{reasons}</ul>
</div>
"""
