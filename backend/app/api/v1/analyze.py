"""
analyze.py — POST /api/v1/analyze
-----------------------------------
Unified hybrid analysis endpoint.
Supports LIVE and UPLOAD modes via the same route.

Route is THIN:
  - Parses and validates form fields
  - Instantiates the correct data source strategy
  - Delegates everything to AnalysisService
  - Returns structured response

No business logic here.
No normalization here.
No analytics here.
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.firebase_auth import verify_token
from app.config import get_settings
from app.ingestion.live_aws import LiveAWSDataSource
from app.ingestion.mock_aws import MockAWSDataSource
from app.ingestion.uploaded_file import UploadedFileDataSource
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()

_PLACEHOLDER_KEY = "your_access_key_id"


def _get_live_source(start_date: str, end_date: str):
    """Return MockAWSDataSource when AWS keys are absent/placeholder, else LiveAWSDataSource."""
    settings = get_settings()
    if not settings.aws_access_key_id or settings.aws_access_key_id == _PLACEHOLDER_KEY:
        logger.warning("AWS keys not configured — using demo data for analyze.")
        return MockAWSDataSource(start_date=start_date, end_date=end_date)
    return LiveAWSDataSource(start_date=start_date, end_date=end_date)


@router.post("/analyze", tags=["Analysis"])
async def analyze(
    data_source: Annotated[str, Form()],
    uid: str = Depends(verify_token),
    start_date: Optional[str] = Form(default=None),
    end_date: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    """
    POST /api/v1/analyze

    Supports two modes:
      LIVE:   data_source=LIVE, start_date, end_date
      UPLOAD: data_source=UPLOAD, file=<csv>
    """
    logger.info("analyze() called — uid=%s, mode=%s", uid, data_source)
    mode = data_source.upper()

    if mode == "LIVE":
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error": {
                        "code": "MISSING_PARAMS",
                        "message": "start_date and end_date are required for LIVE mode.",
                    },
                },
            )
        source = _get_live_source(start_date=start_date, end_date=end_date)

    elif mode == "UPLOAD":
        if file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error": {
                        "code": "MISSING_FILE",
                        "message": "A CSV file is required for UPLOAD mode.",
                    },
                },
            )
        source = UploadedFileDataSource(upload_file=file)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error": {
                    "code": "INVALID_DATA_SOURCE",
                    "message": f"data_source must be 'LIVE' or 'UPLOAD', got: '{data_source}'.",
                },
            },
        )

    return AnalysisService.run_analysis(source)
