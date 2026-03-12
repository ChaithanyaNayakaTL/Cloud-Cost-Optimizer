"""
normalizer.py
-------------
6-step normalization pipeline.

Converts heterogeneous provider data:
  - AWS Cost Explorer JSON response  →  NormalizedCostDataset
  - CSV billing export DataFrame     →  NormalizedCostDataset

Design rules enforced here:
  - No analytics logic.
  - No cloud SDK calls.
  - Fail-fast on schema violations (raises ValueError → caught by service layer).
  - CSV injection prevention applied to all string fields.
  - No data persisted to disk at any point.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

import pandas as pd

from app.normalization.models import (
    NormalizedCostDataset,
    NormalizedCostRecord,
    SourceType,
)

logger = logging.getLogger(__name__)

# ─── CSV column aliases (provider → internal) ─────────────────────────────────

_CSV_COLUMN_MAP: dict[str, str] = {
    # ── Internal names (passthrough) ──────────────────────────────────────────
    "service":        "service",
    "region":         "region",
    "usage_type":     "usage_type",
    "usage_amount":   "usage_amount",
    "cost_amount":    "cost_amount",
    "timestamp":      "timestamp",

    # ── AWS Billing CSV / Cost & Usage Report (CUR) ───────────────────────────
    "productname":                      "service",
    "product/productname":              "service",
    "lineitem/productcode":             "service",
    "product name":                     "service",
    "servicename":                      "service",
    "service name":                     "service",
    "product/region":                   "region",
    "lineitem/availabilityzone":        "region",
    "lineitem/usagetype":               "usage_type",
    "usagetype":                        "usage_type",
    "usage type":                       "usage_type",
    "lineitem/usageamount":             "usage_amount",
    "usageamount":                      "usage_amount",
    "usage amount":                     "usage_amount",
    "lineitem/unblendedcost":           "cost_amount",
    "unblendedcost":                    "cost_amount",
    "unblended cost":                   "cost_amount",
    "blendedcost":                      "cost_amount",
    "blended cost":                     "cost_amount",
    "cost":                             "cost_amount",
    "amount":                           "cost_amount",
    "totalcost":                        "cost_amount",
    "total cost":                       "cost_amount",
    "pretaxcost":                       "cost_amount",
    "pre-tax cost":                     "cost_amount",
    "usagestartdate":                   "timestamp",
    "lineitem/usagestartdate":          "timestamp",
    "bill/billingperiodstartdate":      "timestamp",
    "date":                             "timestamp",
    "start date":                       "timestamp",
    "startdate":                        "timestamp",
    "period start date":                "timestamp",
    "billingperiodstartdate":           "timestamp",

    # ── Azure Cost Management export ──────────────────────────────────────────
    "metername":                        "service",
    "meter name":                       "service",
    "metersubcategory":                 "usage_type",
    "resourcelocation":                 "region",
    "resource location":                "region",
    "costinbillingcurrency":            "cost_amount",
    "cost in billing currency":         "cost_amount",
    "paygcostinbillingcurrency":        "cost_amount",
    "quantity":                         "usage_amount",
    "usagequantity":                    "usage_amount",
    "usage quantity":                   "usage_amount",
    "invoicesectionname":               "region",
    "subscriptionname":                 "region",
    "date":                             "timestamp",
}

_REQUIRED_INTERNAL = {"service", "cost_amount", "timestamp"}

_CSV_INJECTION_PATTERN = re.compile(r"^[=+\-@]")


# ─── Step helpers ─────────────────────────────────────────────────────────────

def _sanitize_string(value: Any) -> str:
    """Step-level CSV injection prevention: strip formula-like prefixes."""
    s = str(value).strip()
    if _CSV_INJECTION_PATTERN.match(s):
        s = "'" + s  # prepend single-quote to neutralise formula
    return s


def _coerce_float(value: Any, field_name: str) -> float:
    """Safe float coercion with explicit failure message."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Cannot coerce '{value}' to float for field '{field_name}'.")


def _coerce_date(value: Any, field_name: str = "timestamp") -> date:
    """Safe date coercion supporting ISO strings and pandas Timestamps."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        raise ValueError(f"Cannot coerce '{value}' to date for field '{field_name}'.")


# ─── AWS Cost Explorer JSON Normalizer ────────────────────────────────────────

def normalize_aws_response(raw: dict[str, Any]) -> NormalizedCostDataset:
    """
    Step 1–6 pipeline for AWS Cost Explorer get_cost_and_usage response.

    Expected structure:
      {
        "ResultsByTime": [
          {
            "TimePeriod": {"Start": "YYYY-MM-DD"},
            "Groups": [
              {
                "Keys": ["SERVICE_NAME"],
                "Metrics": {
                  "UnblendedCost": {"Amount": "123.45", "Unit": "USD"}
                }
              }
            ]
          }
        ]
      }
    """
    records: list[NormalizedCostRecord] = []
    results_by_time = raw.get("ResultsByTime", [])

    if not results_by_time:
        logger.warning("AWS response contained no ResultsByTime entries.")
        return NormalizedCostDataset(records=[], source_type=SourceType.LIVE)

    for period in results_by_time:
        # Step 1: Schema detection
        try:
            period_start: str = period["TimePeriod"]["Start"]
            ts = _coerce_date(period_start)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping period with invalid TimePeriod: %s", exc)
            continue

        for group in period.get("Groups", []):
            try:
                # Step 2: Column mapping
                keys = group.get("Keys", [])
                service = _sanitize_string(keys[0]) if keys else "Unknown"

                metrics = group.get("Metrics", {})
                unblended = metrics.get("UnblendedCost", {})
                raw_cost = unblended.get("Amount", "0")

                # Step 3: Type coercion
                cost = _coerce_float(raw_cost, "cost_amount")

                # Step 4: Data cleaning — skip zero/negative cost rows
                if cost <= 0:
                    continue

                # Step 5: Validation
                # cost > 0 already enforced; timestamp validated above

                # Step 6: Output construction
                records.append(
                    NormalizedCostRecord(
                        service=service,
                        cost_amount=round(cost, 6),
                        timestamp=ts,
                        region=None,
                        usage_type=None,
                        usage_amount=0.0,
                    )
                )

            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed AWS group: %s", exc)
                continue

    logger.info("AWS normalization complete: %d records produced.", len(records))
    return NormalizedCostDataset(records=records, source_type=SourceType.LIVE)


# ─── CSV Billing Export Normalizer ────────────────────────────────────────────

def normalize_csv(df: pd.DataFrame) -> NormalizedCostDataset:
    """
    Step 1–6 pipeline for CSV billing export DataFrames.
    Accepts: AWS billing export, plain CSV with internal column names.
    """
    # Step 1: Schema detection — normalise column names
    df.columns = [c.strip().lower() for c in df.columns]
    rename_map = {
        col: internal
        for col, internal in _CSV_COLUMN_MAP.items()
        if col in df.columns
    }
    df = df.rename(columns=rename_map)

    # Validate required internal fields are present after mapping
    missing = _REQUIRED_INTERNAL - set(df.columns)
    if missing:
        actual_cols = list(df.columns[:15])  # show first 15 to keep message readable
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}. "
            f"Your file has these columns: {actual_cols}. "
            f"Rename or ensure your file contains columns for: service (or ProductName), "
            f"cost_amount (or UnblendedCost / Cost), and timestamp (or Date / UsageStartDate)."
        )

    # Step 2: Retain only internal schema columns
    keep_cols = list(_REQUIRED_INTERNAL | {"region", "usage_type", "usage_amount"} & set(df.columns))
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    # Step 3: Type coercion
    df["cost_amount"] = pd.to_numeric(df["cost_amount"], errors="coerce")
    if "usage_amount" in df.columns:
        df["usage_amount"] = pd.to_numeric(df["usage_amount"], errors="coerce").fillna(0.0)
    else:
        df["usage_amount"] = 0.0

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date

    # Step 4: Data cleaning
    before = len(df)
    df = df.dropna(subset=["cost_amount", "timestamp"])      # remove nulls
    df = df[df["cost_amount"] > 0]                           # no zero/negative costs
    logger.debug("CSV cleaning removed %d rows.", before - len(df))

    # Step 5: Validation
    if df.empty:
        raise ValueError("CSV produced zero valid records after cleaning.")

    if "usage_amount" in df.columns:
        invalid_usage = df[df["usage_amount"] < 0]
        if not invalid_usage.empty:
            logger.warning("Dropping %d rows with negative usage_amount.", len(invalid_usage))
            df = df[df["usage_amount"] >= 0]

    # Step 6: Output construction
    records: list[NormalizedCostRecord] = []
    for _, row in df.iterrows():
        service = _sanitize_string(row["service"])
        region = _sanitize_string(row.get("region", "")) or None
        usage_type = _sanitize_string(row.get("usage_type", "")) or None
        records.append(
            NormalizedCostRecord(
                service=service,
                cost_amount=round(float(row["cost_amount"]), 6),
                timestamp=row["timestamp"],
                region=region,
                usage_type=usage_type,
                usage_amount=float(row.get("usage_amount", 0.0)),
            )
        )

    logger.info("CSV normalization complete: %d records produced.", len(records))
    return NormalizedCostDataset(records=records, source_type=SourceType.UPLOAD)
