"""
recommendations.py — GET /api/v1/recommendations
--------------------------------------------------
Returns advisory recommendations for a date range.
Triggers LIVE ingestion. Auth required.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.auth.firebase_auth import verify_token
from app.config import get_settings
from app.ingestion.live_aws import LiveAWSDataSource
from app.ingestion.mock_aws import MockAWSDataSource
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()

_PLACEHOLDER_KEY = "your_access_key_id"


def _get_source(start_date: str, end_date: str):
    """Return MockAWSDataSource when AWS keys are absent/placeholder, else LiveAWSDataSource."""
    settings = get_settings()
    if not settings.aws_access_key_id or settings.aws_access_key_id == _PLACEHOLDER_KEY:
        logger.warning("AWS keys not configured — using demo data.")
        return MockAWSDataSource(start_date=start_date, end_date=end_date)
    return LiveAWSDataSource(start_date=start_date, end_date=end_date)


@router.get("/recommendations", tags=["Recommendations"])
def get_recommendations(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    uid: str = Depends(verify_token),
) -> dict:
    """
    GET /api/v1/recommendations?start_date=&end_date=

    Returns advisory recommendations per API spec §5.5.
    Field structure: resource_id, issue_type, suggested_action,
    estimated_monthly_savings, risk_level, explanation.
    """
    logger.info("get_recommendations() — uid=%s, %s → %s", uid, start_date, end_date)
    source = _get_source(start_date, end_date)
    result = AnalysisService.run_analysis(source)

    recs = result["data"]["recommendations"]
    total_savings = sum(r["estimated_monthly_savings"] for r in recs)

    return {
        "status": "success",
        "data": recs,
        "metadata": {
            **result["metadata"],
            "total_estimated_savings": round(total_savings, 2),
        },
    }
