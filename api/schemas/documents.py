"""Pydantic schemas for document upload endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response returned after successful document upload."""

    document_id: str
    filename: str
    status: str
    message: str
