"""
app/schemas/profile.py
──────────────────────
Pydantic schema for GET /api/v1/user-profile.
"""
from datetime import datetime

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    user_id: str
    avg_amount: float
    std_amount: float
    transaction_count: int
    frequent_locations: list[str]
    active_hours: list[int]
    baseline_hourly_rate: float
    last_updated: datetime

    model_config = {"from_attributes": True}
