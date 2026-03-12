"""
config.py
---------
Centralised, environment-driven configuration.
All secrets are sourced from environment variables only — never hardcoded.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),   # support both; .env.local overrides
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_version: str = "1.0.0"
    app_title: str = "Cloud Cost Optimisation Advisor"

    # AWS (read-only, Cost Explorer)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"

    # Firebase
    firebase_service_account_json: str = ""

    # Upload limits
    max_upload_size_mb: int = 10

    # CORS
    allowed_origins: str = "http://localhost:5173"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def firebase_service_account_dict(self) -> dict:
        if not self.firebase_service_account_json:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON is not configured.")
        return json.loads(self.firebase_service_account_json)


@lru_cache
def get_settings() -> Settings:
    """Singleton settings instance (cached after first call)."""
    return Settings()
