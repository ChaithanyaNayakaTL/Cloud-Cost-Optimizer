"""
models.py
---------
Unified domain models for the normalization and analytics layers.

These are the ONLY data contracts shared between:
  ingestion  →  normalization  →  analytics  →  recommendation  →  API

Design rule: Do NOT enrich or alter these models inside routes or analytics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional


# ─── Source-Type Enum ─────────────────────────────────────────────────────────

class SourceType(str, Enum):
    LIVE = "LIVE"
    UPLOAD = "UPLOAD"


# ─── Normalized Cost Record ───────────────────────────────────────────────────

@dataclass
class NormalizedCostRecord:
    """Single row in the unified billing dataset."""
    service: str
    cost_amount: float
    timestamp: date
    region: Optional[str] = None
    usage_type: Optional[str] = None
    usage_amount: float = 0.0


# ─── Normalized Cost Dataset ──────────────────────────────────────────────────

@dataclass
class NormalizedCostDataset:
    """
    The unified internal model produced by every ingestion path.
    Analytics MUST only consume this type — never raw provider data.
    """
    records: List[NormalizedCostRecord]
    source_type: SourceType
    ingestion_timestamp: Optional[str] = None

    def is_empty(self) -> bool:
        return len(self.records) == 0


# ─── Analytics Outputs ────────────────────────────────────────────────────────

@dataclass
class AnalysisSummary:
    total_cost: float
    average_daily_cost: float
    top_service: str
    top_service_cost: float


@dataclass
class CostBreakdownItem:
    service: str
    cost: float
    percentage: float


@dataclass
class DailyTrendItem:
    date: str   # ISO date string
    cost: float


@dataclass
class AnalyticsResult:
    summary: AnalysisSummary
    cost_breakdown: List[CostBreakdownItem]
    daily_trend: List[DailyTrendItem]


# ─── Recommendation ───────────────────────────────────────────────────────────

@dataclass
class Recommendation:
    """
    Deterministic advisory recommendation.
    All 6 fields are required per the API specification.
    """
    resource_id: str
    issue_type: str
    suggested_action: str
    estimated_monthly_savings: float
    risk_level: str           # Low | Medium | High
    explanation: str
