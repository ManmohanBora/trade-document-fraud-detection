"""
Multimodal feature fusion.

Combines evidence from the image analytics and NLP branches
into a unified representation. Cross-modal signals (e.g., a
suspiciously altered region near an amount field) are surfaced
as explicit flags.
"""

from __future__ import annotations

import logging

from core.pipeline import FusedEvidence, ImageEvidence, TextEvidence

logger = logging.getLogger(__name__)


class FeatureCombiner:
    """
    Fuses image and text evidence into a single FusedEvidence object.

    Cross-modal analysis identifies correlations between visual
    anomalies and textual inconsistencies — for example, if
    manipulation is detected near a region containing financial data.
    """

    async def fuse(
        self,
        image_evidence: ImageEvidence,
        text_evidence: TextEvidence,
    ) -> FusedEvidence:
        """
        Combine image and text evidence with cross-modal analysis.

        Returns a FusedEvidence object with combined features and
        cross-modal flags.
        """
        cross_modal_flags: list[str] = []

        # Flag 1: Visual manipulation + amount anomaly
        if image_evidence.manipulation_detected and text_evidence.amount is not None:
            cross_modal_flags.append(
                "Visual manipulation detected in document containing financial data"
            )

        # Flag 2: Missing stamp/seal on official document
        if not image_evidence.stamp_seal_detected and text_evidence.invoice_number:
            cross_modal_flags.append(
                "No official stamp/seal detected on numbered invoice document"
            )

        # Flag 3: Layout anomaly + text extraction anomalies
        if image_evidence.layout_anomaly_score > 0.5 and text_evidence.anomalies:
            cross_modal_flags.append(
                "Layout anomalies correlate with text extraction irregularities"
            )

        # Flag 4: Low logo confidence + high-value transaction
        if (
            image_evidence.logo_detected
            and image_evidence.logo_match_score < 0.5
            and text_evidence.amount is not None
            and text_evidence.amount > 100_000
        ):
            cross_modal_flags.append(
                "Unverified logo on high-value transaction document"
            )

        # Flag 5: Signature missing
        if not image_evidence.signature_detected and text_evidence.invoice_number:
            cross_modal_flags.append(
                "No signature detected on formal trade document"
            )

        # Compute fusion confidence (weighted average of component confidences)
        image_conf = self._image_confidence(image_evidence)
        text_conf = self._text_confidence(text_evidence)
        fusion_confidence = 0.5 * image_conf + 0.5 * text_conf

        fused = FusedEvidence(
            image_evidence=image_evidence,
            text_evidence=text_evidence,
            cross_modal_flags=cross_modal_flags,
            fusion_confidence=fusion_confidence,
        )

        logger.info(
            "Feature fusion completed: %d cross-modal flags, confidence=%.2f",
            len(cross_modal_flags),
            fusion_confidence,
        )
        return fused

    @staticmethod
    def _image_confidence(evidence: ImageEvidence) -> float:
        """Aggregate confidence from image analysis components."""
        scores = [
            evidence.signature_confidence,
            evidence.stamp_seal_confidence,
            evidence.logo_match_score,
        ]
        valid_scores = [s for s in scores if s > 0]
        return sum(valid_scores) / max(len(valid_scores), 1)

    @staticmethod
    def _text_confidence(evidence: TextEvidence) -> float:
        """Aggregate confidence from text extraction components."""
        if not evidence.field_confidence:
            return 0.0
        return sum(evidence.field_confidence.values()) / len(evidence.field_confidence)
