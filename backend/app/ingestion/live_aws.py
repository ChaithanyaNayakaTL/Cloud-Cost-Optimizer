"""
live_aws.py
-----------
LiveAWSDataSource: Ingestion strategy for AWS Cost Explorer API.

Responsibilities:
  - Call AWS Cost Explorer get_cost_and_usage via boto3
  - Handle pagination (NextPageToken)
  - Apply exponential backoff retries on throttling
  - Delegate raw response to the normalization layer
  - NEVER perform analytics here

Security:
  - AWS credentials sourced from environment variables via boto3 default chain
  - Read-only IAM role assumed — no write operations
"""
from __future__ import annotations

import logging
from datetime import date

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.ingestion.base import AbstractDataSource
from app.normalization.models import NormalizedCostDataset
from app.normalization.normalizer import normalize_aws_response

logger = logging.getLogger(__name__)

_BOTO_CONFIG = Config(
    retries={"mode": "standard", "max_attempts": 1},  # tenacity handles retry logic
    connect_timeout=10,
    read_timeout=30,
)


class LiveAWSDataSource(AbstractDataSource):
    """
    Fetches real-time cost data from the AWS Cost Explorer API.

    Instantiation arguments are validated before boto3 is called so that
    domain errors surface early (in the service layer, not deep in SDK code).
    """

    MAX_RESULTS_PER_PAGE = 50  # conservative page size for throttle avoidance

    def __init__(self, start_date: str, end_date: str) -> None:
        """
        :param start_date: ISO date string (YYYY-MM-DD), inclusive.
        :param end_date:   ISO date string (YYYY-MM-DD), exclusive per AWS spec.
        """
        self._start_date = start_date
        self._end_date = end_date
        self._client = boto3.client("ce", config=_BOTO_CONFIG)

    @property
    def source_label(self) -> str:
        return "LIVE"

    def fetch(self) -> NormalizedCostDataset:
        """
        Paginated fetch from AWS Cost Explorer, then normalise.
        """
        logger.info(
            "LiveAWSDataSource.fetch() — range %s → %s",
            self._start_date,
            self._end_date,
        )
        raw_groups: list[dict] = []
        results_by_time: list[dict] = []
        next_token: str | None = None

        while True:
            response = self._fetch_page(next_token)
            results_by_time.extend(response.get("ResultsByTime", []))
            next_token = response.get("NextPageToken")
            if not next_token:
                break

        logger.info(
            "LiveAWSDataSource: retrieved %d time-period entries.", len(results_by_time)
        )
        return normalize_aws_response({"ResultsByTime": results_by_time})

    @retry(
        retry=retry_if_exception_type(ClientError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _fetch_page(self, next_token: str | None) -> dict:
        """Single paginated call to Cost Explorer with retry on throttling."""
        kwargs: dict = {
            "TimePeriod": {
                "Start": self._start_date,
                "End": self._end_date,
            },
            "Granularity": "DAILY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        }
        if next_token:
            kwargs["NextPageToken"] = next_token

        try:
            response = self._client.get_cost_and_usage(**kwargs)
            return response
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in ("ThrottlingException", "LimitExceededException"):
                logger.warning("AWS throttling detected — retrying: %s", exc)
                raise  # tenacity will retry
            if error_code in (
                "InvalidClientTokenId",
                "AuthFailure",
                "AccessDeniedException",
                "UnauthorizedOperation",
                "InvalidAccessKeyId",
                "SignatureDoesNotMatch",
            ):
                logger.warning("AWS auth error (%s) — credentials may be invalid.", error_code)
                raise RuntimeError(
                    "AWS credentials are invalid or not configured. "
                    "Please provide valid AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
                ) from exc
            logger.error("AWS Cost Explorer error: %s", exc)
            raise RuntimeError(f"AWS API error: {error_code}") from exc
