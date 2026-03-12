"""
router.py
---------
Aggregates all v1 route modules into a single APIRouter.
This is the only file that knows about route modules.
main.py includes only this router.
"""
from fastapi import APIRouter

from app.api.v1 import (
    analyze,
    cost_breakdown,
    health,
    recommendations,
    summary,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(analyze.router)
api_router.include_router(summary.router)
api_router.include_router(cost_breakdown.router)
api_router.include_router(recommendations.router)
