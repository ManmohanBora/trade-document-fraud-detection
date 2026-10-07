"""
Document layout analyzer.

Analyzes the spatial structure of trade documents to detect
layout anomalies — unusual text placement, missing standard
regions, or structural inconsistencies that suggest tampering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LayoutRegion:
    """A detected structural region of the document."""

    label: str  # "header", "table", "footer", "signature_block", etc.
    x: int
    y: int
    width: int
    height: int
    confidence: float


@dataclass
class LayoutAnalysis:
    """Complete layout analysis result."""

    regions: list[LayoutRegion] = field(default_factory=list)
    anomaly_score: float = 0.0  # 0.0 = normal, 1.0 = highly anomalous
    anomalies: list[str] = field(default_factory=list)
    grid_alignment_score: float = 0.0
    whitespace_ratio: float = 0.0


class LayoutAnalyzer:
    """
    Analyzes document layout structure for anomalies.

    Uses connected component analysis and contour detection to
    identify text blocks, tables, headers, and footers. Compares
    the layout against expected trade document templates.
    """

    # Expected regions in standard trade documents
    EXPECTED_REGIONS = {"header", "body", "table", "footer"}

    def analyze(self, image_path: Path) -> LayoutAnalysis:
        """Analyze the layout structure of a document image."""
        img = cv2.imread(str(image_path))
        if img is None:
            logger.warning("Could not read image: %s", image_path)
            return LayoutAnalysis()

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Step 1: Detect text regions via morphological operations
        regions = self._detect_regions(gray, w, h)

        # Step 2: Classify regions by position
        classified = self._classify_regions(regions, w, h)

        # Step 3: Compute anomaly indicators
        anomalies: list[str] = []
        anomaly_score = 0.0

        # Check for missing expected regions
        found_labels = {r.label for r in classified}
        missing = self.EXPECTED_REGIONS - found_labels
        if missing:
            anomalies.append(f"Missing expected regions: {', '.join(missing)}")
            anomaly_score += 0.2 * len(missing)

        # Check alignment consistency
        alignment_score = self._check_alignment(classified, w)
        if alignment_score < 0.5:
            anomalies.append("Poor text alignment — possible content insertion")
            anomaly_score += 0.3

        # Check whitespace ratio
        whitespace = self._compute_whitespace_ratio(gray)
        if whitespace < 0.1 or whitespace > 0.85:
            anomalies.append(f"Unusual whitespace ratio: {whitespace:.1%}")
            anomaly_score += 0.2

        anomaly_score = min(anomaly_score, 1.0)

        return LayoutAnalysis(
            regions=classified,
            anomaly_score=anomaly_score,
            anomalies=anomalies,
            grid_alignment_score=alignment_score,
            whitespace_ratio=whitespace,
        )

    def _detect_regions(
        self, gray: np.ndarray, width: int, height: int
    ) -> list[tuple[int, int, int, int]]:
        """Detect text block regions using morphological closing."""
        # Binarize
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological closing to merge text into blocks
        kernel_width = max(width // 20, 10)
        kernel_height = max(height // 80, 3)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (kernel_width, kernel_height)
        )
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = width * height * 0.002
        regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(contour)
                regions.append((x, y, w, h))

        # Sort top-to-bottom
        regions.sort(key=lambda r: r[1])
        return regions

    def _classify_regions(
        self,
        regions: list[tuple[int, int, int, int]],
        img_width: int,
        img_height: int,
    ) -> list[LayoutRegion]:
        """Classify detected regions by their position in the document."""
        classified: list[LayoutRegion] = []

        for x, y, w, h in regions:
            cy = y + h / 2
            relative_y = cy / img_height

            if relative_y < 0.15:
                label = "header"
            elif relative_y > 0.85:
                label = "footer"
            elif w > img_width * 0.6 and h > img_height * 0.2:
                label = "table"
            else:
                label = "body"

            classified.append(LayoutRegion(
                label=label, x=x, y=y, width=w, height=h, confidence=0.7,
            ))

        return classified

    @staticmethod
    def _check_alignment(regions: list[LayoutRegion], img_width: int) -> float:
        """Check how well text blocks are aligned (left-margin consistency)."""
        if len(regions) < 2:
            return 1.0

        left_margins = [r.x for r in regions]
        margin_std = np.std(left_margins)
        # Normalize: lower std = better alignment
        max_expected_std = img_width * 0.1
        score = max(0.0, 1.0 - margin_std / max_expected_std)
        return float(score)

    @staticmethod
    def _compute_whitespace_ratio(gray: np.ndarray) -> float:
        """Compute the ratio of whitespace pixels to total pixels."""
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        white_pixels = np.sum(binary == 255)
        total_pixels = binary.size
        return float(white_pixels / total_pixels)
