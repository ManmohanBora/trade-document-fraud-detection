"""Unit tests for cross-field entity validation rules."""

from nlp.entity_validator import EntityValidator
from nlp.field_extractor import ExtractedFields


def test_entity_validator_valid_case() -> None:
    validator = EntityValidator()
    fields = ExtractedFields(
        invoice_number="INV-001",
        buyer_name="Alpha Corp",
        seller_name="Beta Trade Ltd",
        amount=50000.0,
        currency="USD",
        date="2025-11-20",
        hs_code="8471.30",
        container_number="MSCU7829104",
    )
    res = validator.validate(fields)
    assert res.is_valid is True
    assert len(res.anomalies) == 0


def test_entity_validator_anomalies_detected() -> None:
    validator = EntityValidator()
    # Identical buyer/seller, negative amount, invalid HS code chapter
    fields = ExtractedFields(
        invoice_number="INV-002",
        buyer_name="Omega Corp",
        seller_name="Omega Corp",
        amount=-100.0,
        currency="USD",
        date="2025-11-20",
        hs_code="0012.30",
        container_number="MSCU7829104",
    )
    res = validator.validate(fields)
    assert res.is_valid is False
    assert any("Buyer and seller" in a for a in res.anomalies)
    assert any("Non-positive amount" in a for a in res.anomalies)
