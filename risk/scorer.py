"""
Risk scoring engine.

Computes a composite risk score (0–100) from fused evidence,
classifies risk level, generates human-readable reasons,
and produces audit recommendations.

Scoring is deterministic and explainable — every point
contributed is traceable to a specific evidence signal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.config import RiskSettings
from core.pipeline import FusedEvidence, RiskAssessment, RiskLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreContribution:
    """A single contribution to the risk score, for explainability."""

    source: str       # e.g., "image.manipulation", "text.amount_anomaly"
    points: float     # Points added to risk score
    reason: str       # Human-readable explanation
    category: str     # "visual", "textual", "cross_modal"


class RiskScorer:
    """
    Computes risk score from fused multimodal evidence.

    The score is a weighted sum of individual risk signals,
    each capped and documented for auditability.
    """

    def __init__(self, settings: RiskSettings | None = None) -> None:
        self._settings = settings or RiskSettings()

    async def assess(self, fused_evidence: FusedEvidence) -> RiskAssessment:
        """
        Assess risk from fused evidence.

        Returns a RiskAssessment with score, level, reasons,
        and recommendation.
        """
        contributions: list[ScoreContribution] = []

        # ── Visual Risk Signals ─────────────────────────────────────

        img = fused_evidence.image_evidence

        if img.manipulation_detected:
            severity = min(25.0 + len(img.manipulation_regions) * 5.0, 45.0)
            contributions.append(ScoreContribution(
                source="image.manipulation",
                points=severity,
                reason="Suspicious visual alteration detected",
                category="visual",
            ))

        if img.layout_anomaly_score > 0.3:
            points = img.layout_anomaly_score * 25.0
            contributions.append(ScoreContribution(
                source="image.layout_anomaly",
                points=points,
                reason="Unusual document layout structure",
                category="visual",
            ))

        if not img.signature_detected:
            contributions.append(ScoreContribution(
                source="image.missing_signature",
                points=8.0,
                reason="No signature detected",
                category="visual",
            ))

        if not img.stamp_seal_detected:
            contributions.append(ScoreContribution(
                source="image.missing_stamp",
                points=8.0,
                reason="No official stamp or seal detected",
                category="visual",
            ))

        if img.logo_detected and img.logo_match_score < 0.5:
            contributions.append(ScoreContribution(
                source="image.logo_mismatch",
                points=12.0,
                reason="Logo does not match known references",
                category="visual",
            ))

        # ── Textual Risk Signals ────────────────────────────────────

        txt = fused_evidence.text_evidence

        if txt.anomalies:
            total = min(len(txt.anomalies) * 15.0, 40.0)
            contributions.append(ScoreContribution(
                source="text.field_anomalies",
                points=total,
                reason=f"Text anomalies: {'; '.join(txt.anomalies[:3])}",
                category="textual",
            ))

        # Missing critical fields
        missing_critical = []
        if txt.invoice_number is None:
            missing_critical.append("invoice number")
        if txt.amount is None:
            missing_critical.append("amount")
        if txt.date is None:
            missing_critical.append("date")

        if missing_critical:
            contributions.append(ScoreContribution(
                source="text.missing_fields",
                points=len(missing_critical) * 8.0,
                reason=f"Missing critical fields: {', '.join(missing_critical)}",
                category="textual",
            ))

        # ── Cross-Modal Risk Signals ────────────────────────────────

        for flag in fused_evidence.cross_modal_flags:
            contributions.append(ScoreContribution(
                source="cross_modal.flag",
                points=15.0,
                reason=flag,
                category="cross_modal",
            ))

        # ── Compute Final Score ─────────────────────────────────────

        # Direct summation of identified risk signals, capped at 100
        raw_score = sum(c.points for c in contributions)
        risk_score = int(min(round(raw_score), 100))

        # Classify
        if risk_score >= self._settings.high_threshold:
            risk_level = RiskLevel.HIGH
        elif risk_score >= self._settings.medium_threshold:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Generate reasons (top contributors)
        reasons = [c.reason for c in sorted(contributions, key=lambda c: -c.points)]

        # Recommendation
        recommendation = self._generate_recommendation(risk_level, reasons)

        assessment = RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            reasons=reasons,
            recommendation=recommendation,
            requires_human_review=risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM),
        )

        logger.info(
            "Risk assessment: score=%d, level=%s, %d reasons",
            risk_score,
            risk_level.value,
            len(reasons),
        )
        return assessment

    @staticmethod
    def _generate_recommendation(
        risk_level: RiskLevel, reasons: list[str]
    ) -> str:
        """Generate a human-readable audit recommendation."""
        if risk_level == RiskLevel.HIGH:
            return (
                "PRIORITY REVIEW RECOMMENDED. Multiple risk indicators detected. "
                "This document should be reviewed by a senior compliance auditor "
                "before processing. Key concerns: "
                + "; ".join(reasons[:3])
                + "."
            )
        elif risk_level == RiskLevel.MEDIUM:
            return (
                "STANDARD REVIEW RECOMMENDED. Some risk indicators present. "
                "This document should be reviewed as part of normal audit procedures. "
                "Notable findings: "
                + "; ".join(reasons[:2])
                + "."
            )
        else:
            return (
                "LOW RISK — no immediate concerns detected. "
                "Document may proceed through standard processing. "
                "Periodic spot-check recommended per compliance policy."
            )
