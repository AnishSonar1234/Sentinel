"""
app/schemas/feedback.py
───────────────────────
Pydantic schemas for POST /api/v1/feedback.
"""
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    transaction_id: str
    is_fraud: bool


class FeedbackResponse(BaseModel):
    status: str
    message: str
    transaction_id: str
