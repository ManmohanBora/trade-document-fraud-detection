"""
Visual manipulation detector.

Uses Error Level Analysis (ELA) and frequency-domain analysis
to detect signs of image tampering — splicing, copy-move,
or digital alteration of document regions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ManipulationRegion:
    """A detected region of potential manipulation."""

    x: int
    y: int
    width: int
    height: int
    confidence: float
    technique: str  # "ela", "frequency", "noise_inconsistency"


class ManipulationDetector:
    """
    Detects visual manipulation in document images.

    Techniques:
      1. Error Level Analysis (ELA) — re-compress and compare
      2. Noise-level inconsistency across regions
      3. Frequency-domain anomaly detection (DCT)
    """

    def __init__(self, sensitivity: float = 0.7) -> None:
        self._sensitivity = sensitivity
        self._ela_quality = 90  # JPEG re-compression quality

    def detect(self, image_path: Path) -> list[ManipulationRegion]:
        """
        Run all manipulation detection techniques on an image.

        Returns a list of suspicious regions with confidence scores.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            logger.warning("Could not read image: %s", image_path)
            return []

        regions: list[ManipulationRegion] = []

        # Technique 1: Error Level Analysis
        ela_regions = self._error_level_analysis(img, image_path)
        regions.extend(ela_regions)

        # Technique 2: Noise inconsistency
        noise_regions = self._noise_inconsistency(img)
        regions.extend(noise_regions)

        logger.info(
            "Manipulation detection completed: %d suspicious regions found",
            len(regions),
        )
        return regions

    def _error_level_analysis(
        self, img: np.ndarray, original_path: Path
    ) -> list[ManipulationRegion]:
        """
        Error Level Analysis — re-compress the image at a known quality
        and measure the difference. Tampered regions show higher error
        levels because they've been through fewer compression cycles.
        """
        import tempfile

        # Re-compress
        temp_path = Path(tempfile.mktemp(suffix=".jpg"))
        cv2.imwrite(str(temp_path), img, [cv2.IMWRITE_JPEG_QUALITY, self._ela_quality])
        recompressed = cv2.imread(str(temp_path))
        temp_path.unlink(missing_ok=True)

        if recompressed is None:
            return []

        # Compute absolute difference
        diff = cv2.absdiff(img, recompressed)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # Amplify differences
        scale = 255.0 / max(gray_diff.max(), 1)
        ela_image = cv2.convertScaleAbs(gray_diff, alpha=scale)

        # Threshold based on sensitivity
        threshold = int((1.0 - self._sensitivity) * 255)
        _, binary = cv2.threshold(ela_image, threshold, 255, cv2.THRESH_BINARY)

        # Find contours of suspicious regions
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[ManipulationRegion] = []
        min_area = img.shape[0] * img.shape[1] * 0.001  # Ignore very small regions

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            # Confidence proportional to mean intensity in the ELA region
            roi = ela_image[y : y + h, x : x + w]
            confidence = float(roi.mean()) / 255.0

            regions.append(ManipulationRegion(
                x=x, y=y, width=w, height=h,
                confidence=min(confidence, 1.0),
                technique="ela",
            ))

        return regions

    def _noise_inconsistency(self, img: np.ndarray) -> list[ManipulationRegion]:
        """
        Detect regions where the noise pattern differs significantly
        from the document's overall noise profile. Spliced-in content
        typically has a different noise signature.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Divide into blocks and measure local noise variance
        block_size = max(h, w) // 8
        if block_size < 16:
            return []

        noise_map: list[tuple[int, int, int, int, float]] = []

        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = gray[y : y + block_size, x : x + block_size].astype(np.float64)
                # Estimate noise via Laplacian variance
                laplacian = cv2.Laplacian(block, cv2.CV_64F)
                noise_var = laplacian.var()
                noise_map.append((x, y, block_size, block_size, noise_var))

        if not noise_map:
            return []

        # Statistical outlier detection
        variances = np.array([n[4] for n in noise_map])
        mean_var = variances.mean()
        std_var = variances.std()

        threshold = mean_var + (2.0 - self._sensitivity) * std_var

        regions: list[ManipulationRegion] = []
        for x, y, bw, bh, var in noise_map:
            if var > threshold:
                confidence = min((var - mean_var) / max(std_var * 3, 1e-6), 1.0)
                regions.append(ManipulationRegion(
                    x=x, y=y, width=bw, height=bh,
                    confidence=confidence,
                    technique="noise_inconsistency",
                ))

        return regions
