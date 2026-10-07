"""Unit tests for NLP field extractor."""

from nlp.field_extractor import FieldExtractor


def test_field_extractor_typical_invoice() -> None:
    extractor = FieldExtractor()
    sample_text = """
    COMMERCIAL INVOICE
    Invoice No: INV-2026-8819
    Date: 2026-03-15
    Buyer: Nordic Logistics GmbH
    Seller: Pacific Exports Ltd
    HS Code: 8471.30.00
    Container: MSCU7829104
    Total Amount: 145,200.50 USD
    """
    fields = extractor.extract(sample_text)

    assert fields.invoice_number == "INV-2026-8819"
    assert fields.amount == 145200.50
    assert fields.currency == "USD"
    assert fields.date == "2026-03-15"
    assert fields.hs_code == "8471.30.00"
    assert fields.container_number == "MSCU7829104"


def test_field_extractor_partial_text() -> None:
    extractor = FieldExtractor()
    sample_text = "Shipment tariff code HS 8517.62 with total value: $4500.00 EUR"
    fields = extractor.extract(sample_text)

    assert fields.hs_code == "8517.62"
    assert fields.amount == 4500.00
