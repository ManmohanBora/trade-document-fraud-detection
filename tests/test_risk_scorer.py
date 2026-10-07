"""Unit tests for explainable risk scoring engine."""

import pytest
from core.config import RiskSettings
from core.pipeline import FusedEvidence, ImageEvidence, RiskLevel, TextEvidence
from risk.scorer import RiskScorer


@pytest.mark.asyncio
async def test_risk_scorer_high_risk_invoice_001() -> None:
    scorer = RiskScorer(RiskSettings(high_threshold=70, medium_threshold=40))

    # Evidence matching Invoice_001 scenario:
    # 1. Suspicious visual alteration
    # 2. Amount inconsistency
    # 3. Unusual document layout
    image_ev = ImageEvidence(
        signature_detected=False,
        stamp_seal_detected=False,
        manipulation_detected=True,
        manipulation_regions=[{"x": 100, "y": 200, "w": 50, "h": 50}] * 3,
        layout_anomaly_score=0.85,
    )
    text_ev = TextEvidence(
        invoice_number="INV-001",
        amount=250000.0,
        currency="USD",
        anomalies=["Amount inconsistency across sub-tables", "Currency code mismatch"],
    )
    fused_ev = FusedEvidence(
        image_evidence=image_ev,
        text_evidence=text_ev,
        cross_modal_flags=[
            "Visual manipulation detected in document containing financial data",
            "No official stamp/seal detected on numbered invoice document",
        ],
    )

    assessment = await scorer.assess(fused_ev)

    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.risk_score >= 70
    assert assessment.requires_human_review is True
    assert any("visual alteration" in r.lower() or "manipulation" in r.lower() for r in assessment.reasons)
    assert any("layout" in r.lower() for r in assessment.reasons)


@pytest.mark.asyncio
async def test_risk_scorer_low_risk_clean_document() -> None:
    scorer = RiskScorer(RiskSettings(high_threshold=70, medium_threshold=40))

    image_ev = ImageEvidence(
        signature_detected=True,
        signature_confidence=0.95,
        stamp_seal_detected=True,
        stamp_seal_confidence=0.92,
        manipulation_detected=False,
        layout_anomaly_score=0.05,
    )
    text_ev = TextEvidence(
        invoice_number="INV-2026-CLEAN",
        amount=12000.0,
        currency="USD",
        date="2026-01-10",
        anomalies=[],
    )
    fused_ev = FusedEvidence(
        image_evidence=image_ev,
        text_evidence=text_ev,
        cross_modal_flags=[],
    )

    assessment = await scorer.assess(fused_ev)

    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.risk_score < 40
    assert assessment.requires_human_review is False
