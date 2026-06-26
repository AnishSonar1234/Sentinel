"""
app/api/routes/simulate.py
───────────────────────────
POST /api/v1/simulate — generate and analyze a synthetic fraud scenario.

This is the demo weapon. Six scenarios, each calibrated for demo_user
to produce a predictable, visually impressive result.
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.simulate import SimulateRequest
from app.schemas.transaction import TransactionResponse
from app.services.simulation_service import generate_transaction, get_scenario_description

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/simulate", response_model=TransactionResponse, summary="Simulate a fraud scenario")
def simulate_transaction(
    payload: SimulateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Generate a synthetic transaction for the given scenario and run it
    through the full fraud analysis pipeline.

    Scenarios:
    - **normal**       — expected ALLOW
    - **high_amount**  — expected VERIFY or BLOCK
    - **new_location** — expected VERIFY
    - **night_time**   — expected VERIFY
    - **rapid_fire**   — call 5+ times to build velocity → expected BLOCK
    - **full_fraud**   — always BLOCK (hard rule: 40x amount + new loc + 2AM)
    """
    logger.info(f"Simulating scenario '{payload.scenario}' for user '{payload.user_id}'")

    # Generate synthetic transaction
    tx_input = generate_transaction(user_id=payload.user_id, scenario=payload.scenario)

    # Import here to avoid circular imports
    from app.api.routes.transactions import _analyze_transaction

    result = _analyze_transaction(tx_input, request, db)
    return result
