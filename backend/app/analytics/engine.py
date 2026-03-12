"""
engine.py  (Analytics Layer)
----------------------------
Pandas-based analytics engine.

Responsibilities:
  - Consume NormalizedCostDataset
  - Produce AnalyticsResult (summary + breakdown + time-series)
  - ZERO knowledge of ingestion format or provider
  - ZERO recommendation logic here

Design rules:
  - Stateless: every call receives + returns data; no class-level state
  - Pure computation: no I/O, no cloud SDK, no file access
"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

from app.normalization.models import (
    AnalysisSummary,
    AnalyticsResult,
    CostBreakdownItem,
    DailyTrendItem,
    NormalizedCostDataset,
)

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Converts a NormalizedCostDataset to structured analytics outputs.

    All methods are instance methods for testability, but carry no state.
    """

    def run(self, dataset: NormalizedCostDataset) -> AnalyticsResult:
        """
        Entry point: run full analytics pipeline.
        Returns AnalyticsResult consumed by the service layer.
        """
        if dataset.is_empty():
            logger.warning("Analytics engine received empty dataset.")
            return self._empty_result()

        df = self._to_dataframe(dataset)

        summary = self._compute_summary(df)
        cost_breakdown = self._compute_cost_breakdown(df)
        daily_trend = self._compute_daily_trend(df)

        logger.info(
            "Analytics complete — total_cost=%.2f, services=%d, days=%d",
            summary.total_cost,
            len(cost_breakdown),
            len(daily_trend),
        )
        return AnalyticsResult(
            summary=summary,
            cost_breakdown=cost_breakdown,
            daily_trend=daily_trend,
        )

    # ─── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_dataframe(dataset: NormalizedCostDataset) -> pd.DataFrame:
        """Convert dataset records to a typed Pandas DataFrame."""
        rows = [
            {
                "service": r.service,
                "region": r.region,
                "usage_type": r.usage_type,
                "usage_amount": r.usage_amount,
                "cost_amount": r.cost_amount,
                "timestamp": pd.Timestamp(r.timestamp),
            }
            for r in dataset.records
        ]
        df = pd.DataFrame(rows)
        df["cost_amount"] = pd.to_numeric(df["cost_amount"], errors="coerce").fillna(0.0)
        df["usage_amount"] = pd.to_numeric(df["usage_amount"], errors="coerce").fillna(0.0)
        return df

    @staticmethod
    def _compute_summary(df: pd.DataFrame) -> AnalysisSummary:
        total_cost = float(df["cost_amount"].sum())
        num_days = max(df["timestamp"].nunique(), 1)
        avg_daily = total_cost / num_days

        service_totals = df.groupby("service")["cost_amount"].sum()
        top_service = service_totals.idxmax()
        top_cost = float(service_totals.max())

        return AnalysisSummary(
            total_cost=round(total_cost, 2),
            average_daily_cost=round(avg_daily, 2),
            top_service=str(top_service),
            top_service_cost=round(top_cost, 2),
        )

    @staticmethod
    def _compute_cost_breakdown(df: pd.DataFrame) -> List[CostBreakdownItem]:
        total_cost = df["cost_amount"].sum()
        service_totals = (
            df.groupby("service")["cost_amount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        items: List[CostBreakdownItem] = []
        for _, row in service_totals.iterrows():
            cost = float(row["cost_amount"])
            pct = (cost / total_cost * 100) if total_cost > 0 else 0.0
            items.append(
                CostBreakdownItem(
                    service=str(row["service"]),
                    cost=round(cost, 2),
                    percentage=round(pct, 2),
                )
            )
        return items

    @staticmethod
    def _compute_daily_trend(df: pd.DataFrame) -> List[DailyTrendItem]:
        daily = (
            df.groupby("timestamp")["cost_amount"]
            .sum()
            .sort_index()
            .reset_index()
        )
        return [
            DailyTrendItem(
                date=str(row["timestamp"].date()),
                cost=round(float(row["cost_amount"]), 2),
            )
            for _, row in daily.iterrows()
        ]

    @staticmethod
    def _empty_result() -> AnalyticsResult:
        empty_summary = AnalysisSummary(
            total_cost=0.0,
            average_daily_cost=0.0,
            top_service="N/A",
            top_service_cost=0.0,
        )
        return AnalyticsResult(
            summary=empty_summary,
            cost_breakdown=[],
            daily_trend=[],
        )
