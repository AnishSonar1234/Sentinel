"""
app/services/simulation_service.py
────────────────────────────────────
Generates synthetic TransactionInput objects for 6 fraud scenarios.

This is the demo weapon — each scenario is designed to produce a
predictable, visually impressive result when demoing to judges.

Scenarios calibrated for demo_user (avg_amount=250, locations=[Mumbai, Pune]):
    normal       → amount ~$200–$350, Mumbai/Pune, 10:00–18:00 → ALLOW
    high_amount  → amount ~$3000, Mumbai, 14:00             → VERIFY/BLOCK
    new_location → amount ~$280, Lagos, 11:00               → VERIFY
    night_time   → amount ~$220, Mumbai, 03:00              → VERIFY
    rapid_fire   → normal amount, but called N times fast   → BLOCK (velocity)
    full_fraud   → amount $9999, Accra, 02:00               → BLOCK (hard rule)
"""
import random
from datetime import datetime, timezone, timedelta

from app.schemas.transaction import TransactionInput


def _now_at_hour(hour: int) -> datetime:
    """Return today's datetime at the given hour (UTC)."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)


def generate_transaction(user_id: str, scenario: str) -> TransactionInput:
    """
    Generate a single TransactionInput for the given scenario.

    For 'rapid_fire', call this multiple times — the scenario itself
    doesn't inject the velocity; repeated calls to /analyze-transaction do.
    """
    scenarios: dict[str, dict] = {
        "normal": {
            "amount": round(random.uniform(180, 350), 2),
            "location": random.choice(["Mumbai", "Pune"]),
            "merchant_type": random.choice(["grocery", "food", "retail"]),
            "hour": random.randint(10, 17),
        },
        "high_amount": {
            "amount": round(random.uniform(2500, 4000), 2),
            "location": "Mumbai",
            "merchant_type": "electronics",
            "hour": random.randint(10, 17),
        },
        "new_location": {
            "amount": round(random.uniform(200, 350), 2),
            "location": "Lagos",
            "merchant_type": "retail",
            "hour": random.randint(10, 17),
        },
        "night_time": {
            "amount": round(random.uniform(180, 320), 2),
            "location": "Mumbai",
            "merchant_type": "atm",
            "hour": random.randint(1, 4),
        },
        "rapid_fire": {
            # Each call generates a normal-looking txn
            # Velocity accumulates in DB from repeated calls
            "amount": round(random.uniform(100, 300), 2),
            "location": "Mumbai",
            "merchant_type": "retail",
            "hour": random.randint(10, 17),
        },
        "full_fraud": {
            # Designed to always hit the hard-block rule:
            # amount_ratio ≈ 40x, new location, unusual hour
            "amount": round(random.uniform(9000, 12000), 2),
            "location": "Accra",
            "merchant_type": "wire_transfer",
            "hour": random.randint(1, 4),
        },
    }

    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario}")

    cfg = scenarios[scenario]
    return TransactionInput(
        user_id=user_id,
        amount=cfg["amount"],
        location=cfg["location"],
        merchant_type=cfg["merchant_type"],
        timestamp=_now_at_hour(cfg["hour"]),
    )


def get_scenario_description(scenario: str) -> str:
    """Human-readable description of each scenario (for docs/health page)."""
    descriptions = {
        "normal":       "Normal transaction — expected ALLOW",
        "high_amount":  "5–10x usual amount — expected VERIFY or BLOCK",
        "new_location": "Unknown location — expected VERIFY",
        "night_time":   "3AM transaction — expected VERIFY",
        "rapid_fire":   "Repeated calls build up velocity — expected BLOCK after ~5 calls",
        "full_fraud":   "High amount + new location + 2AM — expected BLOCK (hard rule)",
    }
    return descriptions.get(scenario, "Unknown scenario")
