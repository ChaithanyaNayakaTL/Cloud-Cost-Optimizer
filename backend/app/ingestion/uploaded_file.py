"""
uploaded_file.py
----------------
UploadedFileDataSource: Ingestion strategy for billing CSV exports.

Responsibilities:
  - Enforce file size limits BEFORE reading into memory
  - Parse CSV in-memory using Pandas
  - Reject unsupported content types
  - Delegate to normalization layer
  - NEVER persist raw file to disk
  - NEVER perform analytics here
"""
from __future__ import annotations

import io
import logging

import pandas as pd
from fastapi import UploadFile

from app.config import get_settings
from app.ingestion.base import AbstractDataSource
from app.normalization.models import NormalizedCostDataset
from app.normalization.normalizer import normalize_csv

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
}


class UploadedFileDataSource(AbstractDataSource):
    """
    Ingests a billing CSV export uploaded by the user.

    The raw file is never written to disk — it is read into memory,
    parsed, normalized, and then discarded.
    """

    def __init__(self, upload_file: UploadFile) -> None:
        self._upload_file = upload_file
        self._settings = get_settings()

    @property
    def source_label(self) -> str:
        return "UPLOAD"

    def fetch(self) -> NormalizedCostDataset:
        """
        1. Read raw bytes from the uploaded file.
        2. Enforce size limit.
        3. Parse CSV into DataFrame.
        4. Delegate to normalize_csv.
        """
        filename = self._upload_file.filename or "unknown"
        logger.info("UploadedFileDataSource.fetch() — file: %s", filename)

        # Read all bytes in-memory (file is not written to disk)
        raw_bytes: bytes = self._upload_file.file.read()

        # Enforce file size limit
        max_bytes = self._settings.max_upload_size_bytes
        if len(raw_bytes) > max_bytes:
            raise ValueError(
                f"Uploaded file exceeds maximum allowed size of "
                f"{self._settings.max_upload_size_mb} MB. "
                f"Received {len(raw_bytes) / (1024 * 1024):.2f} MB."
            )

        # Validate content type (advisory — rely on schema validation primarily)
        content_type = (self._upload_file.content_type or "").lower()
        if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported file type: '{content_type}'. "
                f"Only CSV files are accepted."
            )

        # Parse CSV
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), low_memory=False)
        except Exception as exc:
            raise ValueError(f"Failed to parse CSV file '{filename}': {exc}") from exc

        logger.debug(
            "CSV parsed: %d rows, %d columns — %s",
            len(df),
            len(df.columns),
            list(df.columns),
        )

        # Delegate normalization
        return normalize_csv(df)
