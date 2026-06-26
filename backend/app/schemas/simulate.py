"""
app/schemas/simulate.py
───────────────────────
Pydantic schema for POST /api/v1/simulate.
"""
from typing import Literal

from pydantic import BaseModel

# All valid scenario names
ScenarioType = Literal[
    "normal",
    "high_amount",
    "new_location",
    "night_time",
    "rapid_fire",
    "full_fraud",
]


class SimulateRequest(BaseModel):
    user_id: str = "demo_user"
    scenario: ScenarioType = "normal"
