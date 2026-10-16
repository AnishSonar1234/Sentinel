"""
app/services/verification_service.py
──────────────────────────────────────
Mock OTP generation and verification.

Fix 2 (OTP Expiry):
    OTP expires 2 minutes after generation.
    Expired OTP → verification fails → transaction decision updated to BLOCK.

⚠️  SIMULATION ONLY — no real SMS/email integration.
    In production, replace generate_otp() delivery with Twilio / SendGrid.
"""
import random
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.verify import VerifyResponse

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 2


def generate_otp() -> str:
    """Generate a random 6-digit OTP string."""
    return str(random.randint(100000, 999999))


def verify_otp(
    transaction_id: str,
    provided_otp: str,
    db: Session,
) -> VerifyResponse:
    """
    Verify OTP for a VERIFY-decision transaction.

    Steps:
      1. Fetch transaction — 404 if not found
      2. Check it's in VERIFY state — error if already ALLOW/BLOCK
      3. Check OTP expiry (Fix 2) — expired → update to BLOCK, return failure
      4. Compare OTP — mismatch → return failure
      5. Match → mark otp_verified=True, return success
    """
    tx = db.query(Transaction).filter_by(transaction_id=transaction_id).first()

    if not tx:
        return VerifyResponse(
            status="failure",
            message=f"Transaction {transaction_id} not found.",
            transaction_id=transaction_id,
        )

    if tx.decision != "VERIFY":
        return VerifyResponse(
            status="failure",
            message=f"Transaction is not pending verification (decision={tx.decision}).",
            transaction_id=transaction_id,
        )

    # Fix 2: OTP expiry check
    if tx.otp_generated_at:
        expiry = tx.otp_generated_at + timedelta(minutes=OTP_EXPIRY_MINUTES)
        if datetime.utcnow() > expiry:
            # Auto-escalate to BLOCK on expired OTP
            tx.decision = "BLOCK"
            db.add(tx)
            db.commit()
            logger.warning(f"OTP expired for {transaction_id} — escalated to BLOCK")
            return VerifyResponse(
                status="failure",
                message="OTP expired (2-minute window). Transaction has been blocked.",
                transaction_id=transaction_id,
            )

    # OTP comparison
    if tx.otp != provided_otp:
        return VerifyResponse(
            status="failure",
            message="Invalid OTP. Please try again.",
            transaction_id=transaction_id,
        )

    # Success
    tx.otp_verified = True
    tx.decision = "ALLOW"
    db.add(tx)
    db.commit()
    logger.info(f"OTP verified successfully for {transaction_id} — decision updated to ALLOW")

    return VerifyResponse(
        status="success",
        message="OTP verified. Transaction approved.",
        transaction_id=transaction_id,
        verified=True,
    )
