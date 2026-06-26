"""
app/api/routes/feedback.py
───────────────────────────
POST /api/v1/feedback — label a transaction as fraud or not-fraud.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.transaction import Transaction
from app.schemas.feedback import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse, summary="Submit fraud label")
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Label a completed transaction as fraud or legitimate.

    Used for:
    - Model feedback loop (future retraining)
    - Audit / dispute trails

    Returns 404 if the transaction doesn't exist.
    """
    tx = db.query(Transaction).filter_by(
        transaction_id=payload.transaction_id
    ).first()

    if not tx:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {payload.transaction_id} not found.",
        )

    tx.feedback_is_fraud = payload.is_fraud
    db.add(tx)
    db.commit()

    label = "FRAUD" if payload.is_fraud else "LEGITIMATE"
    logger.info(f"Feedback received: {payload.transaction_id} → {label}")

    return FeedbackResponse(
        status="success",
        message=f"Transaction labeled as {label}. Thank you for the feedback.",
        transaction_id=payload.transaction_id,
    )
