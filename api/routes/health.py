"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns application name, version, and status.
    Used by Docker health checks and load balancers.
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
