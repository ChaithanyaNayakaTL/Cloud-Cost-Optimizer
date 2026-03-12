"""
engine.py  (Recommendation Layer)
-----------------------------------
Deterministic, rule-based recommendation engine.

Design rules:
  - Explainable logic only (no ML, no probabilities)
  - Conservative thresholds to avoid false positives
  - NO cloud SDK calls
  - NO analytics computation here — consumes AnalyticsResult
  - Returns List[Recommendation] with all 6 required fields per spec
"""
from __future__ import annotations

import logging
from typing import List

from app.normalization.models import (
    AnalyticsResult,
    NormalizedCostDataset,
    Recommendation,
)

logger = logging.getLogger(__name__)

# ─── Thresholds ───────────────────────────────────────────────────────────────

# A service is "dominant" if it accounts for more than this share of total cost
_COST_CONCENTRATION_THRESHOLD = 0.20   # 20%

# Estimated achievable savings when a dominant service is right-sized (conservative)
_SAVINGS_FACTOR_CONCENTRATION = 0.20   # 20%

# A service with zero usage_amount but non-zero cost is flagged
_ZERO_USAGE_THRESHOLD = 0.0

# Minimum cost to emit a recommendation (avoid noise for micro-spend)
_MIN_COST_FOR_RECOMMENDATION = 1.0

# Absolute spend threshold for high-spend recommendation (Rule 3)
_HIGH_SPEND_THRESHOLD = 10.0           # $10 / period (lowered from $50)

# Always recommend on at least this many top services (catch-all Rule 4)
_TOP_SERVICES_ALWAYS_RECOMMEND = 3


class RecommendationEngine:
    """
    Applies deterministic rules to AnalyticsResult and raw dataset records
    to produce explainable, advisory-only recommendations.

    Every recommendation maps to the 6-field schema from the API spec.
    """

    def generate(
        self,
        dataset: NormalizedCostDataset,
        analytics: AnalyticsResult,
    ) -> List[Recommendation]:
        """
        Entry point: run all rules and collect results.
        Returns an empty list if no rules fire (not an error condition).
        """
        if dataset.is_empty():
            return []

        recommendations: List[Recommendation] = []
        # Each rule tracks its own seen-set so one rule doesn't block another
        seen_concentration: set[str] = set()   # Rule 1
        seen_idle: set[str] = set()             # Rule 2
        seen_high_spend: set[str] = set()       # Rule 3
        seen_services: set[str] = set()         # Rule 4 catch-all (any prior rule)
        total_cost = analytics.summary.total_cost

        # ── Aggregate usage per service from raw records ──────────────────────
        # total_usage: sum of all usage_amount per service (used for Rule 2 fallback)
        service_usage: dict[str, float] = {}
        # idle_services: services that have AT LEAST ONE record with zero usage but non-zero cost
        idle_services: set[str] = set()
        for record in dataset.records:
            svc = record.service
            service_usage[svc] = service_usage.get(svc, 0.0) + record.usage_amount
            if record.usage_amount == 0.0 and record.cost_amount > 0:
                idle_services.add(svc)

        logger.info("Idle services detected from records: %s", idle_services)

        for item in analytics.cost_breakdown:
            if item.cost < _MIN_COST_FOR_RECOMMENDATION:
                continue

            usage = service_usage.get(item.service, 0.0)

            # ── Rule 1: Cost Concentration ─────────────────────────────────────
            if (
                item.service not in seen_concentration
                and item.cost / total_cost > _COST_CONCENTRATION_THRESHOLD
            ):
                savings = round(item.cost * _SAVINGS_FACTOR_CONCENTRATION, 2)
                recommendations.append(
                    Recommendation(
                        resource_id=item.service,
                        issue_type="Cost Concentration",
                        suggested_action=(
                            f"Review {item.service} resource configurations. "
                            "Consider Reserved Instances or Savings Plans "
                            "to reduce on-demand spend."
                        ),
                        estimated_monthly_savings=savings,
                        risk_level="Low",
                        explanation=(
                            f"{item.service} accounts for {item.percentage:.1f}% of total cloud spend "
                            f"(${item.cost:.2f}), which exceeds the {_COST_CONCENTRATION_THRESHOLD*100:.0f}% "
                            "concentration threshold. Diversifying or optimizing this service "
                            "could yield significant savings."
                        ),
                    )
                )
                seen_concentration.add(item.service)
                seen_services.add(item.service)

            # ── Rule 2: Zero usage but non-zero cost ───────────────────────────
            # Runs INDEPENDENTLY — a service can be both high-concentration AND idle
            if (
                item.service not in seen_idle
                and usage <= _ZERO_USAGE_THRESHOLD
                and item.cost > 5.0
            ):
                savings = round(item.cost * 0.30, 2)
                recommendations.append(
                    Recommendation(
                        resource_id=item.service,
                        issue_type="Idle Resource Suspected",
                        suggested_action=(
                            f"Audit {item.service} resources for idle or abandoned "
                            "instances. Terminate or right-size resources with "
                            "zero recorded usage."
                        ),
                        estimated_monthly_savings=savings,
                        risk_level="Medium",
                        explanation=(
                            f"{item.service} incurred ${item.cost:.2f} in cost with "
                            "zero recorded usage units. This pattern is consistent "
                            "with idle, reserved, or misconfigured resources."
                        ),
                    )
                )
                seen_idle.add(item.service)
                seen_services.add(item.service)

            # ── Rule 3: High Absolute Spend ────────────────────────────────────
            # Only fires if no other rule already covered this service
            if (
                item.service not in seen_high_spend
                and item.service not in seen_concentration
                and item.service not in seen_idle
                and item.cost >= _HIGH_SPEND_THRESHOLD
            ):
                savings = round(item.cost * 0.15, 2)
                recommendations.append(
                    Recommendation(
                        resource_id=item.service,
                        issue_type="High Spend Detected",
                        suggested_action=(
                            f"Analyse {item.service} usage patterns. "
                            "Review instance types, storage tiers, and data transfer costs. "
                            "Enable Cost Anomaly Detection alerts for this service."
                        ),
                        estimated_monthly_savings=savings,
                        risk_level="Low",
                        explanation=(
                            f"{item.service} spent ${item.cost:.2f} in the selected period. "
                            "A 15% savings estimate is achievable via right-sizing, "
                            "reserved capacity, or eliminating unused resources."
                        ),
                    )
                )
                seen_high_spend.add(item.service)
                seen_services.add(item.service)

        # ── Rule 4: Catch-all for top services ────────────────────────────────
        # Guarantee the top N services by spend ALWAYS get a recommendation,
        # even if they slipped through all threshold-based rules above.
        # cost_breakdown is already sorted descending by cost.
        catch_all_count = 0
        for item in analytics.cost_breakdown:
            if catch_all_count >= _TOP_SERVICES_ALWAYS_RECOMMEND:
                break
            if item.cost < _MIN_COST_FOR_RECOMMENDATION:
                break
            if item.service in seen_services:
                catch_all_count += 1
                continue
            # Emit advisory for any top service not yet covered
            savings = round(item.cost * 0.12, 2)
            recommendations.append(
                Recommendation(
                    resource_id=item.service,
                    issue_type="Top Spending Service",
                    suggested_action=(
                        f"Review {item.service} billing details. "
                        "Consider Reserved Instances, Savings Plans, or right-sizing "
                        "to reduce costs for this top-spending service."
                    ),
                    estimated_monthly_savings=savings,
                    risk_level="Low",
                    explanation=(
                        f"{item.service} is one of your top spending services "
                        f"at ${item.cost:.2f} ({item.percentage:.1f}% of total spend). "
                        "Even a modest 12% reduction through reserved pricing or "
                        "right-sizing would yield meaningful savings."
                    ),
                )
            )
            seen_services.add(item.service)
            catch_all_count += 1

        logger.info(
            "RecommendationEngine: %d recommendation(s) generated.", len(recommendations)
        )
        return recommendations

