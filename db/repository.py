"""
Data access repository for AuditRecord entities.

Encapsulates database operations for saving pipeline audit results
and querying audit histories with filtering, pagination, and review tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuditRecordNotFound
from core.pipeline import AuditResult
from db.models import AuditRecord

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repository managing audit records in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, audit: AuditResult) -> AuditRecord:
        """Persist a completed pipeline AuditResult into PostgreSQL."""
        record = AuditRecord(
            audit_id=audit.audit_id,
            document_id=audit.document.document_id if audit.document else "unknown",
            document_filename=audit.document.filename if audit.document else "unknown",
            document_mime_type=audit.document.mime_type if audit.document else "application/pdf",
            document_size_bytes=audit.document.file_size_bytes if audit.document else 0,
            risk_score=audit.risk_assessment.risk_score if audit.risk_assessment else 0,
            risk_level=audit.risk_assessment.risk_level.value if audit.risk_assessment else "Low",
            risk_reasons=audit.risk_assessment.reasons if audit.risk_assessment else [],
            recommendation=audit.risk_assessment.recommendation if audit.risk_assessment else "",
            invoice_number=audit.text_evidence.invoice_number if audit.text_evidence else None,
            buyer_name=audit.text_evidence.buyer_name if audit.text_evidence else None,
            seller_name=audit.text_evidence.seller_name if audit.text_evidence else None,
            amount=audit.text_evidence.amount if audit.text_evidence else None,
            currency=audit.text_evidence.currency if audit.text_evidence else None,
            hs_code=audit.text_evidence.hs_code if audit.text_evidence else None,
            container_number=audit.text_evidence.container_number if audit.text_evidence else None,
            image_evidence={
                "signature_detected": audit.image_evidence.signature_detected if audit.image_evidence else False,
                "stamp_seal_detected": audit.image_evidence.stamp_seal_detected if audit.image_evidence else False,
                "manipulation_detected": audit.image_evidence.manipulation_detected if audit.image_evidence else False,
                "layout_anomaly_score": audit.image_evidence.layout_anomaly_score if audit.image_evidence else 0.0,
            },
            text_evidence={
                "anomalies": audit.text_evidence.anomalies if audit.text_evidence else [],
                "field_confidence": audit.text_evidence.field_confidence if audit.text_evidence else {},
            },
            cross_modal_flags=audit.fused_evidence.cross_modal_flags if audit.fused_evidence else [],
            ocr_confidence=audit.ocr_result.avg_confidence if audit.ocr_result else None,
            processing_time_seconds=audit.processing_time_seconds,
            pipeline_version=audit.pipeline_version,
        )

        self._session.add(record)
        await self._session.flush()
        logger.info("Persisted audit record %s with score %d", record.audit_id, record.risk_score)
        return record

    async def get_by_id(self, audit_id: str) -> AuditRecord:
        """Fetch an audit record by its UUID."""
        stmt = select(AuditRecord).where(AuditRecord.audit_id == audit_id)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise AuditRecordNotFound(audit_id)
        return record

    async def list_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_level: str | None = None,
    ) -> Sequence[AuditRecord]:
        """Fetch paginated audit records with optional risk filtering."""
        stmt = select(AuditRecord).order_by(desc(AuditRecord.created_at)).limit(limit).offset(offset)
        if risk_level:
            stmt = stmt.where(AuditRecord.risk_level == risk_level)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def record_human_decision(
        self,
        audit_id: str,
        reviewer: str,
        decision: str,
        notes: str | None = None,
    ) -> AuditRecord:
        """Record auditor sign-off and review outcome."""
        record = await self.get_by_id(audit_id)
        record.reviewed_by = reviewer
        record.reviewed_at = datetime.now(timezone.utc)
        record.review_decision = decision
        record.review_notes = notes
        await self._session.flush()
        logger.info("Recorded auditor review for %s by %s: %s", audit_id, reviewer, decision)
        return record
