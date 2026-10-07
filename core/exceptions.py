"""
Custom exception hierarchy for the fraud detection pipeline.

All pipeline-specific exceptions inherit from PipelineError,
enabling granular error handling at the API boundary while
keeping domain logic clean.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


# ── Upload & Preprocessing ─────────────────────────────────────────────

class DocumentUploadError(PipelineError):
    """Raised when document upload fails validation or storage."""
    pass


class UnsupportedDocumentType(DocumentUploadError):
    """Raised for file types not in the allowed extensions list."""

    def __init__(self, filename: str, allowed: list[str]) -> None:
        super().__init__(
            f"Unsupported file type for '{filename}'",
            detail=f"Allowed extensions: {', '.join(allowed)}",
        )
        self.filename = filename
        self.allowed = allowed


class FileTooLarge(DocumentUploadError):
    """Raised when uploaded file exceeds the size limit."""

    def __init__(self, filename: str, size_mb: float, max_mb: int) -> None:
        super().__init__(
            f"File '{filename}' is {size_mb:.1f} MB, exceeds {max_mb} MB limit",
        )


# ── OCR ─────────────────────────────────────────────────────────────────

class OCRError(PipelineError):
    """Raised when OCR processing fails."""
    pass


class OCREngineNotAvailable(OCRError):
    """Raised when the configured OCR engine cannot be initialized."""

    def __init__(self, engine: str) -> None:
        super().__init__(
            f"OCR engine '{engine}' is not available or not installed",
            detail="Check that the engine binary is on PATH and dependencies are met.",
        )


# ── Image Analytics ─────────────────────────────────────────────────────

class ImageAnalyticsError(PipelineError):
    """Raised when image analysis fails."""
    pass


class ModelLoadError(ImageAnalyticsError):
    """Raised when a deep learning model cannot be loaded."""

    def __init__(self, model_name: str, path: str) -> None:
        super().__init__(
            f"Failed to load model '{model_name}' from '{path}'",
            detail="Verify model file exists and is compatible with the current framework version.",
        )


# ── NLP / Document Understanding ───────────────────────────────────────

class NLPError(PipelineError):
    """Raised when NLP processing fails."""
    pass


class FieldExtractionError(NLPError):
    """Raised when required fields cannot be extracted from a document."""

    def __init__(self, document_id: str, missing_fields: list[str]) -> None:
        super().__init__(
            f"Could not extract required fields from document '{document_id}'",
            detail=f"Missing fields: {', '.join(missing_fields)}",
        )
        self.missing_fields = missing_fields


# ── Fusion & Risk ───────────────────────────────────────────────────────

class FusionError(PipelineError):
    """Raised when multimodal feature fusion fails."""
    pass


class RiskAssessmentError(PipelineError):
    """Raised when risk scoring encounters an error."""
    pass


# ── Database ────────────────────────────────────────────────────────────

class DatabaseError(PipelineError):
    """Raised for database connectivity or query errors."""
    pass


class AuditRecordNotFound(DatabaseError):
    """Raised when a queried audit record does not exist."""

    def __init__(self, record_id: str) -> None:
        super().__init__(
            f"Audit record '{record_id}' not found",
        )
        self.record_id = record_id
