"""
base.py
-------
Abstract interface for all data ingestion strategies.

Design: Strategy Pattern.
Every ingestion source MUST implement `fetch()` and return NormalizedCostDataset.
The analytics layer is never aware of which concrete strategy is active.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.normalization.models import NormalizedCostDataset


class AbstractDataSource(ABC):
    """
    Base class for all ingestion strategies.

    Contract:
      - `fetch()` returns a fully normalized dataset.
      - No HTTP/cloud SDK concerns leak outside the concrete class.
      - No analytics logic inside this layer.
    """

    @abstractmethod
    def fetch(self) -> NormalizedCostDataset:
        """Fetch and return a NormalizedCostDataset."""
        ...

    @property
    @abstractmethod
    def source_label(self) -> str:
        """Human-readable label for logging/metadata (e.g. 'LIVE', 'UPLOAD')."""
        ...
