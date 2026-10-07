"""
Audit record retrieval endpoints.

Provides read access to completed audit results stored in PostgreSQL.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get(
    "/audits/{audit_id}",
    summary="Retrieve a completed audit result",
)
async def get_audit(audit_id: str) -> dict:
    """
    Retrieve a single audit result by its ID.

    Returns the full audit record including risk score, risk level,
    reasons, and the human-auditor caveat.
    """
    # TODO: Wire to AuditRepository
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Audit retrieval not yet implemented — database integration pending",
    )


@router.get(
    "/audits",
    summary="List recent audit results",
)
async def list_audits(
    limit: int = 50,
    offset: int = 0,
    risk_level: str | None = None,
) -> dict:
    """
    List audit results with optional filtering by risk level.

    Supports pagination via limit/offset.
    """
    # TODO: Wire to AuditRepository with filtering
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Audit listing not yet implemented — database integration pending",
    )
