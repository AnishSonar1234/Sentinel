"""
app/schemas/transaction.py
──────────────────────────
Pydantic schemas for the /analyze-transaction endpoint.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    """
    Request body for POST /api/v1/analyze-transaction.
    transaction_id is auto-generated if not provided — enables idempotency (Fix 3).
    """
    transaction_id: str = Field(
        default_factory=lambda: f"txn_{uuid.uuid4().hex[:8]}",
        description="Unique transaction ID. If omitted, one is auto-generated.",
    )
    user_id: str = Field(..., description="Unique identifier for the user")
    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    location: str = Field(..., description="Transaction location (city or country)")
    merchant_type: Optional[str] = Field(
        None, description="Merchant category (e.g. electronics, food, travel)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Transaction timestamp (UTC). Defaults to now.",
    )


class TransactionResponse(BaseModel):
    """Response body for POST /api/v1/analyze-transaction."""
    transaction_id: str
    user_id: str
    amount: float
    decision: str           # ALLOW | VERIFY | BLOCK
    risk_score: float       # 0–100 fused score
    rule_score: float       # 0–1 rule engine component
    anomaly_score: Optional[float]  # None if hard rule short-circuited (Fix 4)
    reasons: list[str]      # top-3 structured reason codes
    otp: Optional[str] = None  # only present when decision == VERIFY

    model_config = {"from_attributes": True}


class TransactionListItem(BaseModel):
    """Compact transaction summary for GET /api/v1/transactions."""
    transaction_id: str
    user_id: str
    amount: float
    location: str
    decision: str
    risk_score: float
    reasons: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
