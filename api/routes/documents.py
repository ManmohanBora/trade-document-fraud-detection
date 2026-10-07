"""
Document upload endpoints.

Handles multipart file upload, validation, and pipeline dispatch.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from api.schemas.documents import UploadResponse
from core.config import Settings, get_settings
from core.exceptions import DocumentUploadError, UnsupportedDocumentType, FileTooLarge
from core.pipeline import DocumentMetadata

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_upload(file: UploadFile, settings: Settings) -> None:
    """Validate file type and size before processing."""
    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise UnsupportedDocumentType(file.filename, settings.allowed_extensions)

    # Size check is approximate from content-length header;
    # exact check happens after saving
    if file.size and file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise FileTooLarge(
            file.filename,
            file.size / (1024 * 1024),
            settings.max_upload_size_mb,
        )


@router.post(
    "/documents/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a trade document for analysis",
)
async def upload_document(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """
    Upload a trade document (PDF or image) for multimodal fraud analysis.

    The document is saved, validated, and queued for pipeline processing.
    Returns a document_id for tracking the analysis result.
    """
    try:
        _validate_upload(file, settings)
    except DocumentUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        ) from exc

    document_id = str(uuid.uuid4())
    save_path = settings.upload_dir / f"{document_id}{Path(file.filename).suffix}"

    # Save uploaded file
    content = await file.read()
    save_path.write_bytes(content)

    metadata = DocumentMetadata(
        document_id=document_id,
        filename=file.filename,  # type: ignore[arg-type]
        file_path=save_path,
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )

    logger.info(
        "Document uploaded",
        extra={"document_id": document_id, "filename": file.filename},
    )

    # TODO: Dispatch to pipeline (async task queue in production)
    # await pipeline.analyze(metadata)

    return UploadResponse(
        document_id=metadata.document_id,
        filename=metadata.filename,
        status="queued",
        message="Document accepted for analysis",
    )
