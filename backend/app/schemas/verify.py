"""
app/schemas/verify.py
─────────────────────
Pydantic schemas for POST /api/v1/verify-transaction.
"""
from pydantic import BaseModel


class VerifyRequest(BaseModel):
    transaction_id: str
    otp: str


class VerifyResponse(BaseModel):
    status: str          # "success" | "failure"
    message: str
    transaction_id: str
