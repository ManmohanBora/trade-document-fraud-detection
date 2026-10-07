"""
FastAPI application entrypoint.

Provides REST endpoints for document upload, pipeline execution,
and audit record retrieval. Uses dependency injection for all
pipeline components.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, documents, audits
from core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    settings.ensure_directories()
    logger.info(
        "Starting %s v%s",
        settings.app_name,
        settings.app_version,
    )
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Multi-Modal AI Pipeline for Trade Document "
            "Fraud Detection & Compliance Auditing. "
            "AI-generated risk indicators — not proof of fraud."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — restrictive in production, permissive in debug
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501"] if not settings.debug else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Register route modules
    app.include_router(health.router, tags=["Health"])
    app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
    app.include_router(audits.router, prefix="/api/v1", tags=["Audits"])

    return app


app = create_app()
