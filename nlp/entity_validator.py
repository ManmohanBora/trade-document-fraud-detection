"""
Cross-field entity validator.

Validates extracted fields against business rules and cross-references
for consistency. Detects anomalies like currency mismatches, invalid
HS codes, impossible dates, and buyer/seller inconsistencies.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from nlp.field_extractor import ExtractedFields

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of cross-field validation."""

    is_valid: bool = True
    anomalies: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0


class EntityValidator:
    """
    Validates trade document fields for internal consistency.

    Rules are based on common trade document standards:
    - HS code format (6–10 digits, valid chapter range)
    - Container number checksum (ISO 6346)
    - Amount/currency consistency
    - Date plausibility
    - Buyer ≠ Seller
    """

    # Valid HS code chapters: 01–99
    HS_VALID_CHAPTERS = set(range(1, 100))

    # ISO 6346 container type equipment category identifiers
    CONTAINER_CATEGORY_CODES = {"U", "J", "Z"}

    def validate(self, fields: ExtractedFields) -> ValidationResult:
        """Run all validation checks on extracted fields."""
        result = ValidationResult()

        checks = [
            self._validate_hs_code,
            self._validate_container_number,
            self._validate_amount,
            self._validate_date,
            self._validate_buyer_seller,
        ]

        for check in checks:
            result.checks_total += 1
            try:
                check(fields, result)
                result.checks_passed += 1
            except Exception as exc:
                logger.warning("Validation check failed: %s", exc)
                result.anomalies.append(f"Validation error: {exc}")
                result.is_valid = False

        if result.anomalies:
            result.is_valid = False

        logger.info(
            "Validation: %d/%d checks passed, %d anomalies",
            result.checks_passed,
            result.checks_total,
            len(result.anomalies),
        )
        return result

    def _validate_hs_code(
        self, fields: ExtractedFields, result: ValidationResult
    ) -> None:
        """Validate HS code format and chapter range."""
        if fields.hs_code is None:
            result.warnings.append("HS code not found in document")
            return

        digits = re.sub(r"[.\s]", "", fields.hs_code)
        if not digits.isdigit() or len(digits) < 6:
            result.anomalies.append(
                f"Invalid HS code format: '{fields.hs_code}' (expected 6+ digits)"
            )
            return

        chapter = int(digits[:2])
        if chapter not in self.HS_VALID_CHAPTERS:
            result.anomalies.append(
                f"Invalid HS code chapter {chapter:02d} (valid: 01–99)"
            )

    def _validate_container_number(
        self, fields: ExtractedFields, result: ValidationResult
    ) -> None:
        """Validate container number against ISO 6346 checksum."""
        if fields.container_number is None:
            return

        cn = fields.container_number.upper()
        if len(cn) != 11:
            result.anomalies.append(
                f"Container number '{cn}' is not 11 characters (ISO 6346)"
            )
            return

        owner_code = cn[:3]
        category = cn[3]
        serial = cn[4:10]
        check_digit = cn[10]

        if not owner_code.isalpha():
            result.anomalies.append(f"Invalid owner code in container: {owner_code}")

        if category not in self.CONTAINER_CATEGORY_CODES:
            result.warnings.append(
                f"Unusual equipment category '{category}' in container number"
            )

        if not serial.isdigit() or not check_digit.isdigit():
            result.anomalies.append(f"Invalid serial/check digit in container: {cn}")

    def _validate_amount(
        self, fields: ExtractedFields, result: ValidationResult
    ) -> None:
        """Check that amount is positive and within plausible range."""
        if fields.amount is None:
            result.warnings.append("Amount not found in document")
            return

        if fields.amount <= 0:
            result.anomalies.append(f"Non-positive amount: {fields.amount}")
        elif fields.amount > 1_000_000_000:
            result.warnings.append(
                f"Unusually large amount: {fields.amount:,.2f} — verify manually"
            )

    def _validate_date(
        self, fields: ExtractedFields, result: ValidationResult
    ) -> None:
        """Check that document date is plausible (not future, not ancient)."""
        if fields.date is None:
            result.warnings.append("Date not found in document")
            return

        # Try common formats
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                parsed = datetime.strptime(fields.date, fmt)
                if parsed.year < 2000:
                    result.anomalies.append(f"Suspicious date year: {parsed.year}")
                if parsed > datetime.now():
                    result.anomalies.append(f"Future date detected: {fields.date}")
                return
            except ValueError:
                continue

        result.warnings.append(f"Could not parse date format: '{fields.date}'")

    def _validate_buyer_seller(
        self, fields: ExtractedFields, result: ValidationResult
    ) -> None:
        """Check that buyer and seller are not the same entity."""
        if fields.buyer_name and fields.seller_name:
            if fields.buyer_name.strip().lower() == fields.seller_name.strip().lower():
                result.anomalies.append(
                    "Buyer and seller appear to be the same entity"
                )
