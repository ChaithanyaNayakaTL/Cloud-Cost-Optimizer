"""
analysis_service.py
--------------------
Service layer: orchestrates the full analysis pipeline.

Responsibilities:
  - Coordinate: fetch → analytics → recommendations
  - Own ALL business logic (no logic in routes)
  - Return structured response models to API layer
  - Translate domain errors into HTTP-appropriate exceptions

Design contract:
  - Routes call this; routes do NOT call ingestion/analytics/recommendations directly
  - This layer has no knowledge of HTTP (no Request, no Response objects)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.analytics.engine import AnalyticsEngine
from app.ingestion.base import AbstractDataSource
from app.normalization.models import (
    AnalyticsResult,
    NormalizedCostDataset,
    Recommendation,
)
from app.recommendations.engine import RecommendationEngine

logger = logging.getLogger(__name__)

_analytics_engine = AnalyticsEngine()
_recommendation_engine = RecommendationEngine()


class AnalysisService:
    """
    Thin orchestration wrapper around the analytics pipeline.

    Stateless: every call creates fresh results.
    """

    @staticmethod
    def run_analysis(data_source: AbstractDataSource) -> dict:
        """
        Execute the full pipeline for a given data source strategy.

        Returns a dict matching the /analyze response schema.
        Raises HTTPException on known failure modes.
        """
        label = data_source.source_label
        logger.info("AnalysisService.run_analysis() — source=%s", label)

        # 1. Fetch + normalise (delegation to ingestion strategy)
        try:
            dataset: NormalizedCostDataset = data_source.fetch()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "error",
                    "error": {
                        "code": "NORMALIZATION_ERROR",
                        "message": str(exc),
                    },
                },
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "error",
                    "error": {
                        "code": "AWS_API_FAILURE",
                        "message": str(exc),
                    },
                },
            )

        # 2. Analytics
        analytics: AnalyticsResult = _analytics_engine.run(dataset)

        # 3. Recommendations
        recs: list[Recommendation] = _recommendation_engine.generate(dataset, analytics)

        # 4. Build response payload
        timestamp_utc = datetime.now(timezone.utc).isoformat()

        return {
            "status": "success",
            "data": {
                "summary": {
                    "total_cost": analytics.summary.total_cost,
                    "average_daily_cost": analytics.summary.average_daily_cost,
                    "top_service": analytics.summary.top_service,
                    "top_service_cost": analytics.summary.top_service_cost,
                },
                "cost_breakdown": [
                    {
                        "service": item.service,
                        "cost": item.cost,
                        "percentage": item.percentage,
                    }
                    for item in analytics.cost_breakdown
                ],
                "recommendations": [
                    {
                        "resource_id": r.resource_id,
                        "issue_type": r.issue_type,
                        "suggested_action": r.suggested_action,
                        "estimated_monthly_savings": r.estimated_monthly_savings,
                        "risk_level": r.risk_level,
                        "explanation": r.explanation,
                    }
                    for r in recs
                ],
                "daily_trend": [
                    {"date": t.date, "cost": t.cost}
                    for t in analytics.daily_trend
                ],
            },
            "metadata": {
                "data_source": label,
                "analysis_timestamp": timestamp_utc,
                "record_count": len(dataset.records),
                "recommendation_count": len(recs),
            },
        }
