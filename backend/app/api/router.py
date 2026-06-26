"""
app/api/router.py
──────────────────
Central API router — registers all route modules under /api/v1 prefix.
"""
from fastapi import APIRouter

from app.api.routes import feedback, health, simulate, transactions, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(transactions.router, tags=["Transactions"])
api_router.include_router(feedback.router,     tags=["Feedback"])
api_router.include_router(users.router,        tags=["Users"])
api_router.include_router(simulate.router,     tags=["Simulation"])
api_router.include_router(health.router,       tags=["Health"])
