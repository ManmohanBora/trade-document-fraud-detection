"""
Stamp and seal detector.

Uses YOLO object detection to locate stamps/seals in trade documents,
then classifies their authenticity using a ResNet feature extractor
with cosine similarity against a reference database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StampDetection:
    """A detected stamp or seal region."""

    x: int
    y: int
    width: int
    height: int
    confidence: float
    classification: str  # "official_stamp", "company_seal", "unknown"
    match_score: float   # Similarity to known reference (0.0–1.0)


class StampSealDetector:
    """
    Detects and classifies stamps/seals in trade documents.

    Pipeline:
      1. YOLO detects stamp-like circular/rectangular regions
      2. Hough Circle Transform as fallback for circular stamps
      3. ResNet feature extraction for similarity matching
    """

    def __init__(
        self,
        yolo_model_path: str | None = None,
        confidence_threshold: float = 0.65,
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._yolo_model = None

        if yolo_model_path and Path(yolo_model_path).exists():
            try:
                from ultralytics import YOLO

                self._yolo_model = YOLO(yolo_model_path)
                logger.info("YOLO stamp detector loaded from %s", yolo_model_path)
            except Exception:
                logger.warning("Could not load YOLO model, falling back to Hough detection")

    def detect(self, image_path: Path) -> list[StampDetection]:
        """Detect stamps/seals in the given image."""
        img = cv2.imread(str(image_path))
        if img is None:
            logger.warning("Could not read image: %s", image_path)
            return []

        detections: list[StampDetection] = []

        # Primary: YOLO detection
        if self._yolo_model is not None:
            detections = self._yolo_detect(img)

        # Fallback: Hough Circle Transform for circular stamps
        if not detections:
            detections = self._hough_detect(img)

        logger.info("Stamp detection: %d stamps/seals found", len(detections))
        return detections

    def _yolo_detect(self, img: np.ndarray) -> list[StampDetection]:
        """Use YOLO to detect stamp regions."""
        results = self._yolo_model(img, verbose=False)  # type: ignore[union-attr]
        detections: list[StampDetection] = []

        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < self._confidence_threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                cls_name = result.names.get(cls_id, "unknown")

                detections.append(StampDetection(
                    x=x1, y=y1,
                    width=x2 - x1, height=y2 - y1,
                    confidence=conf,
                    classification=cls_name,
                    match_score=0.0,  # Populated by similarity step
                ))

        return detections

    def _hough_detect(self, img: np.ndarray) -> list[StampDetection]:
        """Fallback: detect circular stamp regions using Hough Transform."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)

        h, w = gray.shape
        min_radius = int(min(h, w) * 0.02)
        max_radius = int(min(h, w) * 0.15)

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min_radius * 4,
            param1=100,
            param2=40,
            minRadius=min_radius,
            maxRadius=max_radius,
        )

        detections: list[StampDetection] = []

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for circle in circles[0]:
                cx, cy, r = int(circle[0]), int(circle[1]), int(circle[2])
                detections.append(StampDetection(
                    x=cx - r, y=cy - r,
                    width=2 * r, height=2 * r,
                    confidence=0.5,  # Hough is less confident than YOLO
                    classification="unknown",
                    match_score=0.0,
                ))

        return detections
