"""
app/api/routes/transactions.py
───────────────────────────────
POST /api/v1/analyze-transaction  — core fraud scoring endpoint
POST /api/v1/verify-transaction   — OTP verification
GET  /api/v1/transactions         — transaction history

The _analyze_transaction() function is the heart of Sentinel.
It is also called by /simulate to reuse the exact same pipeline.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionInput,
    TransactionListItem,
    TransactionResponse,
)
from app.schemas.verify import VerifyRequest, VerifyResponse
from app.services.behavior_engine import BehaviorEngine
from app.services.decision_engine import fuse_scores, make_decision
from app.services.explainability_engine import ExplainabilityEngine
from app.services.ml_engine_service import MLEngineService
from app.services.rules_engine import RulesEngine
from app.services.verification_service import generate_otp, verify_otp
from app.services.agent_investigator import AgentInvestigator

logger = logging.getLogger(__name__)
router = APIRouter()

# Instantiate stateless service objects once (they hold no DB state)
_behavior_engine = BehaviorEngine()
_rules_engine = RulesEngine()
_explain_engine = ExplainabilityEngine()


# ── Core analysis pipeline ─────────────────────────────────────────────────────

def _analyze_transaction(
    tx: TransactionInput,
    request: Request,
    db: Session,
) -> TransactionResponse:
    """
    Full fraud analysis pipeline. Called by both the API route and /simulate.

    Steps:
      [0] Idempotency check (Fix 3)
      [1] Get/create user profile
      [2] Compute velocity (live DB count)
      [3] Build feature vector (with new-user fallback — Fix 1)
      [4] Hard-rule check (Fix 4 — short-circuit before ML)
      [5] Soft rules + ML scoring (if no hard block)
      [6] Fuse scores → risk_score → decision
      [7] Generate OTP if VERIFY (Fix 2 — store timestamp)
      [8] Build reason codes
      [9] Persist transaction
     [10] Update user profile (Welford)
    """
    # ── [0] Idempotency check (Fix 3) ─────────────────────────────────────────
    existing = (
        db.query(Transaction)
        .filter_by(transaction_id=tx.transaction_id)
        .first()
    )
    if existing:
        logger.info(f"Idempotent return for transaction {tx.transaction_id}")
        return _tx_to_response(existing)

    # ── [1] Load user profile ──────────────────────────────────────────────────
    profile = _behavior_engine.get_or_create_profile(tx.user_id, db)

    # ── [2] Velocity check ─────────────────────────────────────────────────────
    tx_time = tx.timestamp
    if tx_time.tzinfo is not None:
        tx_time = tx_time.replace(tzinfo=None)  # SQLite stores naive datetimes

    txn_count_1h = _behavior_engine.get_velocity(tx.user_id, tx_time, db)

    # ── [3] Build feature vector (Fix 1 applied inside) ───────────────────────
    features = _behavior_engine.compute_features(tx, profile, txn_count_1h)

    # ── [4] Hard-rule check (Fix 4 — skip ML entirely if triggered) ───────────
    is_hard, hard_reason_str = _rules_engine.is_hard_block(features)

    otp_value: Optional[str] = None
    otp_generated_at: Optional[datetime] = None

    if is_hard:
        decision = "BLOCK"
        risk_score = 100.0
        rule_score_val = 1.0
        anomaly_score_val = None   # ML was not called
        reasons = [hard_reason_str]
        logger.warning(f"Hard block triggered for {tx.transaction_id}: {hard_reason_str}")

    else:
        # ── [5a] Soft rules ────────────────────────────────────────────────────
        rule_result = _rules_engine.evaluate(features)

        # ── [5b] ML scoring ───────────────────────────────────────────────────
        predictor = getattr(request.app.state, "predictor", None)
        ml_service = MLEngineService(predictor)
        anomaly_score_val = ml_service.score(features)

        # ── [6] Score fusion + decision ────────────────────────────────────────
        risk_score = fuse_scores(rule_result.score, anomaly_score_val)
        decision = make_decision(risk_score)
        rule_score_val = rule_result.score

        # ── [7] OTP generation (Fix 2 — store generated_at for expiry) ────────
        if decision == "VERIFY":
            otp_value = generate_otp()
            otp_generated_at = datetime.utcnow()
            logger.info(f"OTP generated for {tx.transaction_id}: {otp_value}")

        # ── [8] Reason codes ───────────────────────────────────────────────────
        reasons = _explain_engine.generate_reasons(
            features, rule_result, hard_block=False
        )

    # ── [9] Persist transaction ────────────────────────────────────────────────
    tx_naive = tx_time  # already stripped tz above
    db_tx = Transaction(
        transaction_id=tx.transaction_id,
        user_id=tx.user_id,
        amount=tx.amount,
        location=tx.location,
        merchant_type=tx.merchant_type,
        timestamp=tx_naive,
        risk_score=risk_score,
        rule_score=rule_score_val,
        anomaly_score=anomaly_score_val,
        decision=decision,
        reasons=json.dumps(reasons),
        otp=otp_value,
        otp_generated_at=otp_generated_at,
        otp_verified=False,
        feedback_is_fraud=None,
        created_at=datetime.utcnow(),
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)

    # ── [10] Update profile (Welford) ──────────────────────────────────────────
    _behavior_engine.update_profile(profile, tx, db)

    logger.info(
        f"Transaction {tx.transaction_id} → {decision} "
        f"(risk={risk_score}, user={tx.user_id})"
    )

    return TransactionResponse(
        transaction_id=tx.transaction_id,
        user_id=tx.user_id,
        amount=tx.amount,
        decision=decision,
        risk_score=risk_score,
        rule_score=round(rule_score_val, 4),
        anomaly_score=anomaly_score_val,
        reasons=reasons,
        otp=otp_value,
    )


def _tx_to_response(tx: Transaction) -> TransactionResponse:
    """Convert a persisted Transaction ORM object → TransactionResponse."""
    return TransactionResponse(
        transaction_id=tx.transaction_id,
        user_id=tx.user_id,
        amount=tx.amount,
        decision=tx.decision,
        risk_score=tx.risk_score,
        rule_score=tx.rule_score,
        anomaly_score=tx.anomaly_score,
        reasons=json.loads(tx.reasons or "[]"),
        otp=tx.otp,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/analyze-transaction",
    response_model=TransactionResponse,
    summary="Analyze a transaction for fraud risk",
)
def analyze_transaction(
    payload: TransactionInput,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Core fraud scoring endpoint.

    Accepts a transaction and returns:
    - **decision**: ALLOW | VERIFY | BLOCK
    - **risk_score**: 0–100 (fused rule + ML score)
    - **reasons**: top-3 human-readable explanations
    - **otp**: 6-digit code (only present when decision = VERIFY)
    """
    return _analyze_transaction(payload, request, db)


@router.post(
    "/verify-transaction",
    response_model=VerifyResponse,
    summary="Verify an OTP for a VERIFY-decision transaction",
)
def verify_transaction(
    payload: VerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Verify the OTP for a transaction that received decision=VERIFY.

    - Correct OTP within 2 minutes → success
    - Correct OTP but expired → failure + transaction escalated to BLOCK
    - Wrong OTP → failure
    """
    return verify_otp(payload.transaction_id, payload.otp, db)


@router.get(
    "/transactions",
    response_model=list[TransactionListItem],
    summary="List transactions",
)
def list_transactions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    decision: Optional[str] = Query(None, description="Filter by decision (ALLOW/VERIFY/BLOCK)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List recent transactions with optional filters.
    Returns compact summaries suitable for a dashboard view.
    """
    query = db.query(Transaction)

    if user_id:
        query = query.filter(Transaction.user_id == user_id)
    if decision:
        query = query.filter(Transaction.decision == decision.upper())

    txns = (
        query.order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        TransactionListItem(
            transaction_id=tx.transaction_id,
            user_id=tx.user_id,
            amount=tx.amount,
            location=tx.location,
            decision=tx.decision,
            risk_score=tx.risk_score,
            reasons=json.loads(tx.reasons or "[]"),
            created_at=tx.created_at,
        )
        for tx in txns
    ]


@router.get(
    "/investigate/{transaction_id}",
    summary="Agentic Workflow: Deep LLM Investigation",
    description="Invokes the AI Copilot to review a transaction against the user's history and generate a Suspicious Activity Report (SAR)."
)
def investigate_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    """
    Agentic Workflow: Generates a SAR using an LLM.
    """
    tx = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    profile = _behavior_engine.get_or_create_profile(tx.user_id, db)
    
    agent = AgentInvestigator()
    report = agent.investigate(tx, profile)
    
    return report
