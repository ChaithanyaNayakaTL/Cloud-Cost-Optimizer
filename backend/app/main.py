"""
main.py
-------
FastAPI application entry point.

Responsibilities:
  - Register middleware (exception, logging, CORS)
  - Mount the central API router
  - Serve the app via Uvicorn

Design rules:
  - No business logic here
  - No route handlers here (all routes in api/v1/)
  - Middleware must NOT expose internal stack traces to clients
"""
from __future__ import annotations

import logging
import time
import traceback

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings

# ─── Logging setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── App initialisation ───────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Logging Middleware ───────────────────────────────────────────────────────

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log request metadata and execution duration for every request."""
    start = time.perf_counter()
    logger.info(
        "→ %s %s | client=%s",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
    )
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "← %s %s | status=%d | %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ─── Global Exception Middleware ──────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    Returns structured error; suppresses internal stack trace from client.
    """
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
        },
    )


# ─── Router ───────────────────────────────────────────────────────────────────

app.include_router(api_router)

# ─── Entry point (for local dev: uvicorn app.main:app --reload) ───────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
