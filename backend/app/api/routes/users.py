"""
app/api/routes/users.py
────────────────────────
GET /api/v1/user-profile — fetch a user's behavioral profile.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.behavior_profile import UserBehaviorProfile
from app.schemas.profile import UserProfileResponse

router = APIRouter()


@router.get("/user-profile", response_model=UserProfileResponse, summary="Get user behavior profile")
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """
    Returns the behavioral profile for a given user_id.

    Includes:
    - Running average and std of transaction amounts (Welford's)
    - Frequent locations (up to 10)
    - Active hours (list of hour integers)
    - Baseline hourly transaction rate
    """
    profile = (
        db.query(UserBehaviorProfile)
        .filter_by(user_id=user_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No profile found for user '{user_id}'. "
                   "Submit a transaction first.",
        )

    return UserProfileResponse(
        user_id=profile.user_id,
        avg_amount=profile.avg_amount,
        std_amount=profile.std_amount,
        transaction_count=profile.transaction_count,
        frequent_locations=json.loads(profile.frequent_locations or "[]"),
        active_hours=json.loads(profile.active_hours or "[]"),
        baseline_hourly_rate=profile.baseline_hourly_rate,
        last_updated=profile.last_updated,
    )
