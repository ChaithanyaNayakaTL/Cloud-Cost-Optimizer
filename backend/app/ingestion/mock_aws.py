"""
mock_aws.py
-----------
MockAWSDataSource: Returns realistic demo data when AWS keys are not configured.

Used as a drop-in replacement for LiveAWSDataSource so the app can be
demonstrated and tested without real AWS credentials.

The mock generates 30 days of plausible AWS cost data across common services.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.ingestion.base import AbstractDataSource
from app.normalization.models import NormalizedCostDataset, NormalizedCostRecord, SourceType

logger = logging.getLogger(__name__)

# Realistic daily cost breakdown per service (USD)
_MOCK_SERVICE_COSTS: dict[str, float] = {
    "Amazon EC2":               142.50,
    "Amazon S3":                 28.30,
    "Amazon RDS":                87.00,
    "AWS Lambda":                 4.20,
    "Amazon CloudFront":         12.80,
    "Amazon CloudWatch":          6.50,
    "AWS Data Transfer":         18.40,
    "Amazon DynamoDB":           22.10,
    "Amazon EKS":                54.60,
    "Amazon Route 53":            3.90,
}

_MOCK_REGION = "us-east-1"


class MockAWSDataSource(AbstractDataSource):
    """
    Returns deterministic demo cost records.
    Simulates 30 days of AWS spend across common services.
    """

    def __init__(self, start_date: str, end_date: str) -> None:
        self._start_date = start_date
        self._end_date = end_date

    @property
    def source_label(self) -> str:
        return "MOCK"

    def fetch(self) -> NormalizedCostDataset:
        logger.info(
            "MockAWSDataSource.fetch() — generating demo data for %s → %s",
            self._start_date,
            self._end_date,
        )
        records: list[NormalizedCostRecord] = []

        try:
            start = date.fromisoformat(self._start_date)
            end = date.fromisoformat(self._end_date)
        except ValueError:
            start = date.today() - timedelta(days=30)
            end = date.today()

        # Clamp to at most 365 days to avoid huge outputs
        if (end - start).days > 365:
            start = end - timedelta(days=30)

        current = start
        day_index = 0
        while current < end:
            for service, base_daily_cost in _MOCK_SERVICE_COSTS.items():
                # Add slight variation by day (±15%) to make trend charts interesting
                variation = 1.0 + 0.15 * ((day_index % 7 - 3) / 10.0)
                cost = round(base_daily_cost * variation, 4)
                records.append(
                    NormalizedCostRecord(
                        service=service,
                        cost_amount=cost,
                        timestamp=current,
                        region=_MOCK_REGION,
                        usage_type="BoxUsage",
                        usage_amount=1.0,
                    )
                )
            current += timedelta(days=1)
            day_index += 1

        logger.info("MockAWSDataSource: generated %d demo records.", len(records))
        return NormalizedCostDataset(
            records=records,
            source_type=SourceType.LIVE,   # reuse LIVE so analytics pipeline works unchanged
        )
