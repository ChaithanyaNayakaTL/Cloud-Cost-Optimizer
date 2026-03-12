"""
summary.py — GET /api/v1/summary
----------------------------------
Returns aggregated cost summary for a date range.
Triggers LIVE ingestion from AWS Cost Explorer.
Auth required.
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


@router.get("/summary", tags=["Analysis"])
def get_summary(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    uid: str = Depends(verify_token),
) -> dict:
    """
    GET /api/v1/summary?start_date=&end_date=

    Returns summary metrics per API spec §5.3.
    """
    logger.info("get_summary() — uid=%s, %s → %s", uid, start_date, end_date)
    source = _get_source(start_date, end_date)
    result = AnalysisService.run_analysis(source)
    return {
        "status": "success",
        "data": result["data"]["summary"],
        "metadata": result["metadata"],
    }
