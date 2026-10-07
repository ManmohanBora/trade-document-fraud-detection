"""
SQLAlchemy ORM models for audit records.

Maps pipeline output to PostgreSQL tables with proper indexing,
constraints, and JSON columns for semi-structured evidence data.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class AuditRecord(Base):
    """
    Persistent audit record for a processed trade document.

    Stores the full pipeline output: extracted fields, evidence
    from both analysis branches, fused results, and risk assessment.
    """

    __tablename__ = "audit_records"
    __table_args__ = (
        Index("ix_audit_risk_level", "risk_level"),
        Index("ix_audit_created_at", "created_at"),
        Index("ix_audit_document_filename", "document_filename"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Risk assessment
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        Enum("Low", "Medium", "High", name="risk_level_enum"),
        nullable=False,
    )
    risk_reasons: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    # Extracted fields (structured)
    invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hs_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    container_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Semi-structured evidence (stored as JSON)
    image_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    text_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cross_modal_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # OCR metadata
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Processing metadata
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pipeline_version: Mapped[str] = mapped_column(String(20), nullable=False, default="0.1.0")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Human review status
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Caveat is always attached
    CAVEAT = (
        "AI-generated risk indicator — not proof of fraud. "
        "Final decision remains with the human auditor."
    )

    def __repr__(self) -> str:
        return (
            f"<AuditRecord(audit_id={self.audit_id!r}, "
            f"risk_score={self.risk_score}, risk_level={self.risk_level!r})>"
        )
