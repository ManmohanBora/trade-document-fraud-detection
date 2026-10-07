"""
LayoutLMv3 integration for layout-aware document understanding.

Uses the pre-trained LayoutLMv3 model to understand the spatial
relationship between text and layout — crucial for trade documents
where the *position* of information (e.g., amounts in a table vs.
a header) is as meaningful as the text itself.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LayoutLMAnalyzer:
    """
    Layout-aware document analysis using LayoutLMv3.

    Combines text tokens, 2D positional embeddings, and document
    image patches to produce rich representations that capture
    both content and spatial structure.
    """

    def __init__(
        self,
        model_name: str = "microsoft/layoutlmv3-base",
        max_seq_length: int = 512,
        device: str = "cpu",
    ) -> None:
        self._model_name = model_name
        self._max_seq_length = max_seq_length
        self._device = device
        self._model = None
        self._processor = None

    def _load_model(self) -> None:
        """Lazy-load the model on first inference call."""
        if self._model is not None:
            return

        try:
            from transformers import (
                LayoutLMv3ForTokenClassification,
                LayoutLMv3Processor,
            )

            self._processor = LayoutLMv3Processor.from_pretrained(
                self._model_name, apply_ocr=False
            )
            self._model = LayoutLMv3ForTokenClassification.from_pretrained(
                self._model_name
            )
            self._model.to(self._device)
            self._model.eval()

            logger.info("LayoutLMv3 loaded: %s on %s", self._model_name, self._device)
        except Exception as exc:
            logger.error("Failed to load LayoutLMv3: %s", exc)
            raise

    def analyze(
        self,
        text_tokens: list[str],
        bounding_boxes: list[list[int]],
        image_path: str,
    ) -> dict[str, Any]:
        """
        Run layout-aware analysis on a document.

        Args:
            text_tokens: OCR-extracted word tokens
            bounding_boxes: Corresponding [x0, y0, x1, y1] boxes (normalized 0–1000)
            image_path: Path to the document page image

        Returns:
            Dictionary with token classifications and layout features
        """
        self._load_model()

        from PIL import Image
        import torch

        image = Image.open(image_path).convert("RGB")

        # Prepare inputs
        encoding = self._processor(
            image,
            text_tokens,
            boxes=bounding_boxes,
            max_length=self._max_seq_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Move to device
        encoding = {k: v.to(self._device) for k, v in encoding.items()}

        # Inference
        with torch.no_grad():
            outputs = self._model(**encoding)

        logits = outputs.logits
        predictions = torch.argmax(logits, dim=-1).squeeze().tolist()

        # Map predictions back to tokens
        token_labels = []
        for i, (token, pred) in enumerate(zip(text_tokens, predictions)):
            label = self._model.config.id2label.get(pred, "O")
            token_labels.append({"token": token, "label": label, "index": i})

        # Extract layout features
        layout_features = self._extract_layout_features(bounding_boxes)

        return {
            "token_classifications": token_labels,
            "layout_features": layout_features,
            "num_tokens_processed": len(text_tokens),
        }

    @staticmethod
    def _extract_layout_features(boxes: list[list[int]]) -> dict[str, float]:
        """
        Compute spatial layout statistics from bounding boxes.

        These features help detect structural anomalies like
        misaligned fields or unusual text placement.
        """
        if not boxes:
            return {}

        import numpy as np

        boxes_arr = np.array(boxes)
        x_coords = boxes_arr[:, 0]
        y_coords = boxes_arr[:, 1]
        widths = boxes_arr[:, 2] - boxes_arr[:, 0]
        heights = boxes_arr[:, 3] - boxes_arr[:, 1]

        return {
            "mean_x": float(x_coords.mean()),
            "std_x": float(x_coords.std()),
            "mean_y": float(y_coords.mean()),
            "std_y": float(y_coords.std()),
            "mean_width": float(widths.mean()),
            "mean_height": float(heights.mean()),
            "text_density": float(len(boxes) / max(boxes_arr[:, 3].max(), 1)),
            "vertical_spread": float(y_coords.max() - y_coords.min()),
        }
