"""
OCR engine abstraction.

Provides a unified interface over Tesseract and EasyOCR,
selected via configuration. Handles PDF-to-image conversion,
DPI normalization, and structured output with bounding boxes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from core.config import OCRSettings
from core.exceptions import OCRError, OCREngineNotAvailable
from core.pipeline import DocumentMetadata, OCRResult

logger = logging.getLogger(__name__)


class BaseOCREngine(ABC):
    """Abstract OCR engine interface."""

    @abstractmethod
    async def extract(self, document: DocumentMetadata) -> OCRResult:
        """Extract text and word-level bounding boxes from a document."""
        ...


class TesseractEngine(BaseOCREngine):
    """Tesseract OCR engine wrapper."""

    def __init__(self, settings: OCRSettings) -> None:
        self._language = settings.language
        self._dpi = settings.dpi
        self._preprocessing = settings.preprocessing_enabled

        try:
            import pytesseract  # noqa: F401
        except ImportError as exc:
            raise OCREngineNotAvailable("tesseract") from exc

    async def extract(self, document: DocumentMetadata) -> OCRResult:
        """Run Tesseract OCR on the document."""
        import pytesseract
        from PIL import Image

        pages = self._load_pages(document.file_path)
        all_text_parts: list[str] = []
        all_boxes: list[dict[str, Any]] = []
        total_conf = 0.0
        word_count = 0

        for page_path in pages:
            img = Image.open(page_path)
            if self._preprocessing:
                img = self._preprocess(img)

            # Full text
            text = pytesseract.image_to_string(img, lang=self._language)
            all_text_parts.append(text)

            # Word-level data
            data = pytesseract.image_to_data(img, lang=self._language, output_type=pytesseract.Output.DICT)
            for i, word in enumerate(data["text"]):
                if word.strip():
                    conf = float(data["conf"][i])
                    all_boxes.append({
                        "text": word,
                        "bbox": [data["left"][i], data["top"][i], data["width"][i], data["height"][i]],
                        "confidence": conf / 100.0,
                    })
                    total_conf += conf / 100.0
                    word_count += 1

        avg_conf = total_conf / max(word_count, 1)

        return OCRResult(
            full_text="\n\n".join(all_text_parts),
            word_boxes=all_boxes,
            page_images=pages,
            language_detected=self._language,
            avg_confidence=avg_conf,
        )

    def _load_pages(self, file_path: Path) -> list[Path]:
        """Convert PDF to images or return the image path directly."""
        if file_path.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path

            images = convert_from_path(str(file_path), dpi=self._dpi)
            page_paths: list[Path] = []
            for i, img in enumerate(images):
                page_path = file_path.parent / f"{file_path.stem}_page_{i}.png"
                img.save(page_path, "PNG")
                page_paths.append(page_path)
            return page_paths
        return [file_path]

    @staticmethod
    def _preprocess(img):
        """Basic preprocessing: grayscale, contrast enhancement."""
        from PIL import ImageEnhance, ImageFilter

        img = img.convert("L")  # Grayscale
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)
        return img


class EasyOCREngine(BaseOCREngine):
    """EasyOCR engine wrapper."""

    def __init__(self, settings: OCRSettings) -> None:
        self._language = settings.language
        try:
            import easyocr

            self._reader = easyocr.Reader([self._language], gpu=False)
        except ImportError as exc:
            raise OCREngineNotAvailable("easyocr") from exc

    async def extract(self, document: DocumentMetadata) -> OCRResult:
        """Run EasyOCR on the document."""
        results = self._reader.readtext(str(document.file_path))

        full_text_parts: list[str] = []
        word_boxes: list[dict[str, Any]] = []
        total_conf = 0.0

        for bbox, text, conf in results:
            full_text_parts.append(text)
            word_boxes.append({
                "text": text,
                "bbox": bbox,
                "confidence": conf,
            })
            total_conf += conf

        avg_conf = total_conf / max(len(results), 1)

        return OCRResult(
            full_text=" ".join(full_text_parts),
            word_boxes=word_boxes,
            page_images=[document.file_path],
            language_detected=self._language,
            avg_confidence=avg_conf,
        )


def create_ocr_engine(settings: OCRSettings) -> BaseOCREngine:
    """Factory function — instantiates the configured OCR engine."""
    engines = {
        "tesseract": TesseractEngine,
        "easyocr": EasyOCREngine,
    }
    engine_cls = engines.get(settings.engine)
    if engine_cls is None:
        raise OCREngineNotAvailable(settings.engine)

    logger.info("Initializing OCR engine: %s", settings.engine)
    return engine_cls(settings)
