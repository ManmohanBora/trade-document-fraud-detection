"""
Main multimodal pipeline orchestrator.

Coordinates the full document analysis flow:
  Upload → Preprocessing → Parallel Analysis → Fusion → Risk → Recommendation

Each stage is independently testable; the pipeline composes them with
explicit data contracts (dataclasses) and structured logging.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Data Contracts ──────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    """Risk classification levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass(frozen=True)
class DocumentMetadata:
    """Metadata extracted from an uploaded trade document."""

    document_id: str
    filename: str
    file_path: Path
    file_size_bytes: int
    mime_type: str
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OCRResult:
    """Raw OCR output with confidence scores."""

    full_text: str
    word_boxes: list[dict[str, Any]]  # [{text, bbox, confidence}, ...]
    page_images: list[Path]
    language_detected: str
    avg_confidence: float


@dataclass
class ImageEvidence:
    """Evidence gathered from visual/image analysis branch."""

    signature_detected: bool = False
    signature_confidence: float = 0.0
    stamp_seal_detected: bool = False
    stamp_seal_confidence: float = 0.0
    logo_detected: bool = False
    logo_match_score: float = 0.0
    layout_anomaly_score: float = 0.0
    manipulation_detected: bool = False
    manipulation_regions: list[dict[str, Any]] = field(default_factory=list)
    raw_features: dict[str, float] = field(default_factory=dict)


@dataclass
class TextEvidence:
    """Evidence gathered from NLP / document understanding branch."""

    invoice_number: str | None = None
    buyer_name: str | None = None
    seller_name: str | None = None
    amount: float | None = None
    currency: str | None = None
    date: str | None = None
    country_origin: str | None = None
    country_destination: str | None = None
    hs_code: str | None = None
    container_number: str | None = None
    field_confidence: dict[str, float] = field(default_factory=dict)
    layout_features: dict[str, Any] = field(default_factory=dict)
    anomalies: list[str] = field(default_factory=list)


@dataclass
class FusedEvidence:
    """Combined evidence from both analysis branches."""

    image_evidence: ImageEvidence
    text_evidence: TextEvidence
    cross_modal_flags: list[str] = field(default_factory=list)
    fusion_confidence: float = 0.0


@dataclass
class RiskAssessment:
    """Final risk assessment output."""

    risk_score: int  # 0–100
    risk_level: RiskLevel
    reasons: list[str]
    recommendation: str
    requires_human_review: bool = True


@dataclass
class AuditResult:
    """
    Complete pipeline output for one document.

    This is the record persisted to PostgreSQL and displayed
    on the Streamlit compliance dashboard.
    """

    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document: DocumentMetadata | None = None
    ocr_result: OCRResult | None = None
    image_evidence: ImageEvidence | None = None
    text_evidence: TextEvidence | None = None
    fused_evidence: FusedEvidence | None = None
    risk_assessment: RiskAssessment | None = None
    processing_time_seconds: float = 0.0
    pipeline_version: str = "0.1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Caveat attached to every result
    CAVEAT: str = (
        "AI-generated risk indicator — not proof of fraud. "
        "Final decision remains with the human auditor."
    )


# ── Pipeline Orchestrator ──────────────────────────────────────────────


class MultiModalPipeline:
    """
    Orchestrates the full multimodal analysis pipeline.

    Each stage is injected via constructor so components can be
    swapped, mocked, or upgraded independently.
    """

    def __init__(
        self,
        preprocessor,       # preprocessing.ocr_engine.OCREngine
        image_analyzer,     # image_analytics module
        nlp_analyzer,       # nlp module
        feature_fuser,      # fusion.feature_combiner.FeatureCombiner
        risk_scorer,        # risk.scorer.RiskScorer
        audit_repository,   # db.repository.AuditRepository
    ) -> None:
        self._preprocessor = preprocessor
        self._image_analyzer = image_analyzer
        self._nlp_analyzer = nlp_analyzer
        self._feature_fuser = feature_fuser
        self._risk_scorer = risk_scorer
        self._audit_repo = audit_repository

    async def analyze(self, document: DocumentMetadata) -> AuditResult:
        """
        Run the full pipeline on a single trade document.

        Returns an AuditResult containing all evidence, risk score,
        and human-audit recommendation.
        """
        start_time = time.perf_counter()
        audit = AuditResult(document=document)

        logger.info(
            "Pipeline started",
            extra={"document_id": document.document_id, "filename": document.filename},
        )

        # Stage 1: OCR + Preprocessing
        audit.ocr_result = await self._preprocessor.process(document)
        logger.info("OCR completed", extra={"confidence": audit.ocr_result.avg_confidence})

        # Stage 2: Parallel analysis branches
        # In production these run concurrently via asyncio.gather
        audit.image_evidence = await self._image_analyzer.analyze(
            page_images=audit.ocr_result.page_images,
            document_id=document.document_id,
        )

        audit.text_evidence = await self._nlp_analyzer.analyze(
            text=audit.ocr_result.full_text,
            word_boxes=audit.ocr_result.word_boxes,
            document_id=document.document_id,
        )

        # Stage 3: Multimodal Feature Fusion
        audit.fused_evidence = await self._feature_fuser.fuse(
            image_evidence=audit.image_evidence,
            text_evidence=audit.text_evidence,
        )

        # Stage 4: Risk Assessment + Recommendation
        audit.risk_assessment = await self._risk_scorer.assess(
            fused_evidence=audit.fused_evidence,
        )

        audit.processing_time_seconds = time.perf_counter() - start_time

        # Stage 5: Persist audit record
        await self._audit_repo.save(audit)

        logger.info(
            "Pipeline completed",
            extra={
                "document_id": document.document_id,
                "risk_score": audit.risk_assessment.risk_score,
                "risk_level": audit.risk_assessment.risk_level.value,
                "time_seconds": f"{audit.processing_time_seconds:.2f}",
            },
        )

        return audit
