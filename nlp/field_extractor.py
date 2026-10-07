"""
Structured field extractor for trade documents.

Uses regex patterns and heuristic rules to extract key fields
from OCR text. This module works alongside LayoutLMv3 —
regex extraction handles well-structured fields while the
transformer handles ambiguous or layout-dependent content.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFields:
    """Fields extracted from a trade document."""

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
    confidence: dict[str, float] = field(default_factory=dict)
    raw_matches: dict[str, str] = field(default_factory=dict)


class FieldExtractor:
    """
    Extracts structured fields from OCR text using pattern matching.

    Each extraction method returns (value, confidence) tuples.
    Confidence reflects regex match quality, not semantic correctness.
    """

    # ── Compiled Patterns ───────────────────────────────────────────

    # Invoice number: INV-2024-001, Invoice No. 12345, etc.
    INVOICE_NUMBER_PATTERN = re.compile(
        r"(?:invoice\s*(?:no\.?|number|#)\s*[:.]?\s*)"
        r"([A-Z0-9][\w\-/]{2,20})",
        re.IGNORECASE,
    )

    # Monetary amount: $1,234.56 or 1234.56 USD
    AMOUNT_PATTERN = re.compile(
        r"(?:total|amount|value|sum)\s*[:.]?\s*"
        r"(?:[$€£¥])?\s*([\d,]+\.?\d*)\s*"
        r"([A-Z]{3})?",
        re.IGNORECASE,
    )

    # Currency code: USD, EUR, GBP, etc.
    CURRENCY_PATTERN = re.compile(r"\b(USD|EUR|GBP|JPY|CNY|INR|AED|SGD|HKD|CHF)\b")

    # Date patterns: 2024-01-15, 15/01/2024, Jan 15, 2024
    DATE_PATTERN = re.compile(
        r"(?:date\s*[:.]?\s*)?"
        r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    )

    # HS Code: 6-10 digit harmonized system code
    HS_CODE_PATTERN = re.compile(
        r"(?:HS\s*(?:code|tariff)?\s*[:.]?\s*|tariff\s*[:.]?\s*)"
        r"(\d{4}[\.\s]?\d{2}(?:[\.\s]?\d{2,4})?)",
        re.IGNORECASE,
    )

    # Container number: ABCU1234567 (4 letters + 7 digits, ISO 6346)
    CONTAINER_PATTERN = re.compile(
        r"\b([A-Z]{4}\d{7})\b",
    )

    # Bill of Lading number
    BOL_PATTERN = re.compile(
        r"(?:B/?L\s*(?:no\.?|number|#)?\s*[:.]?\s*|bill\s*of\s*lading\s*[:.]?\s*)"
        r"([A-Z0-9][\w\-/]{4,25})",
        re.IGNORECASE,
    )

    def extract(self, text: str) -> ExtractedFields:
        """Extract all structured fields from OCR text."""
        fields = ExtractedFields()

        # Invoice number
        match = self.INVOICE_NUMBER_PATTERN.search(text)
        if match:
            fields.invoice_number = match.group(1).strip()
            fields.confidence["invoice_number"] = 0.85
            fields.raw_matches["invoice_number"] = match.group(0)

        # Amount and currency
        match = self.AMOUNT_PATTERN.search(text)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                fields.amount = float(amount_str)
                fields.confidence["amount"] = 0.80
            except ValueError:
                pass
            if match.group(2):
                fields.currency = match.group(2)
                fields.confidence["currency"] = 0.90

        # Currency (standalone search if not found with amount)
        if fields.currency is None:
            match = self.CURRENCY_PATTERN.search(text)
            if match:
                fields.currency = match.group(1)
                fields.confidence["currency"] = 0.75

        # Date
        match = self.DATE_PATTERN.search(text)
        if match:
            fields.date = match.group(1).strip()
            fields.confidence["date"] = 0.80

        # HS Code
        match = self.HS_CODE_PATTERN.search(text)
        if match:
            fields.hs_code = match.group(1).strip()
            fields.confidence["hs_code"] = 0.85

        # Container number
        match = self.CONTAINER_PATTERN.search(text)
        if match:
            fields.container_number = match.group(1)
            fields.confidence["container_number"] = 0.90

        extracted_count = sum(
            1
            for v in [
                fields.invoice_number,
                fields.amount,
                fields.currency,
                fields.date,
                fields.hs_code,
                fields.container_number,
            ]
            if v is not None
        )

        logger.info("Field extraction: %d/6 key fields found", extracted_count)
        return fields
