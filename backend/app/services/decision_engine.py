"""
app/services/decision_engine.py
────────────────────────────────
Score fusion and final decision logic.

Fuses rule_score + anomaly_score into a single risk_score [0–100].
Applies decision thresholds to produce ALLOW / VERIFY / BLOCK.
"""
from config.settings import settings


def fuse_scores(rule_score: float, anomaly_score: float) -> float:
    """
    Combine rules-based and ML scores into a single risk score [0–100].

    Weights:
        60% rule_score  — interpretable, auditable, human-designed
        40% anomaly_score — ML-driven pattern detection

    We weight rules higher because they are directly explainable to judges
    and to the business. ML acts as a second opinion.
    """
    fused = (0.60 * rule_score + 0.40 * anomaly_score) * 100
    return round(min(max(fused, 0.0), 100.0), 2)


def make_decision(risk_score: float) -> str:
    """
    Apply tiered decision thresholds.

    < ALLOW_THRESHOLD  (40)  → ALLOW   (low risk, proceed normally)
    < BLOCK_THRESHOLD  (75)  → VERIFY  (medium risk, require OTP confirmation)
    ≥ BLOCK_THRESHOLD  (75)  → BLOCK   (high risk, transaction rejected)
    """
    if risk_score < settings.allow_threshold:
        return "ALLOW"
    if risk_score < settings.block_threshold:
        return "VERIFY"
    return "BLOCK"
