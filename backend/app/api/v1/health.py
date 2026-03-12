"""
health.py — GET /api/v1/health
--------------------------------
No authentication required. Used by monitoring and deployment health checks.
"""
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()


@router.get("/health", tags=["Monitoring"])
def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "success",
        "data": {
            "service": "cloud-cost-advisor",
            "version": settings.app_version,
            "status": "running",
        },
    }
