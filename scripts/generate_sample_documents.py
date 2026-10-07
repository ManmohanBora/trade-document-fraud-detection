"""
Generate synthetic trade documents for pipeline testing and live demonstration.

Generates:
1. Invoice_001.pdf (High Risk: Tampered amount, suspicious layout, mismatched font)
2. Bill_of_Lading_772.pdf (Medium Risk: Unregistered stamp, date sequence issue)
3. Customs_Dec_409.pdf (Low Risk: Compliant clean document)

Outputs both .png and .pdf versions to data/samples/ with visual tamper overlays.
"""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def _draw_stamp(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    center_y: int,
    radius: int,
    text: str,
    color: tuple[int, int, int],
    tampered: bool = False,
) -> None:
    """Draw a realistic circular company stamp/seal."""
    # Outer circle
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        outline=color,
        width=3,
    )
    # Inner circle
    inner_r = radius - 8
    draw.ellipse(
        [center_x - inner_r, center_y - inner_r, center_x + inner_r, center_y + inner_r],
        outline=color,
        width=1 if not tampered else 3,
    )
    # Center text
    draw.text((center_x - 35, center_y - 8), text, fill=color)


def generate_invoice_001(out_dir: Path) -> Path:
    """Generate Invoice_001 with visual tamper and amount inconsistency."""
    width, height = 1240, 1754  # A4 150 DPI
    img = Image.new("RGB", (width, height), color=(252, 252, 252))
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([60, 50, width - 60, 140], fill=(15, 23, 42))
    draw.text((80, 75), "COMMERCIAL INVOICE", fill=(255, 255, 255))
    draw.text((width - 320, 85), "ORIGINAL · INTERNATIONAL", fill=(148, 163, 184))

    # Metadata Block
    draw.text((70, 170), "Invoice No: INV-89104-DE", fill=(15, 23, 42))
    draw.text((70, 200), "Date of Issue: 2026-03-12", fill=(71, 85, 105))
    draw.text((70, 230), "Currency: EUR", fill=(71, 85, 105))
    draw.text((width - 450, 170), "Shipper: Global Precision Tools GmbH", fill=(15, 23, 42))
    draw.text((width - 450, 200), "Consignee: Pacific Pacific Imports Pte", fill=(71, 85, 105))
    draw.text((width - 450, 230), "Port of Loading: Hamburg (DEHAM)", fill=(71, 85, 105))

    # Divider line
    draw.line([60, 270, width - 60, 270], fill=(203, 213, 225), width=2)

    # Line Items Table
    draw.rectangle([60, 300, width - 60, 340], fill=(241, 245, 249))
    draw.text((80, 312), "Item / Description", fill=(15, 23, 42))
    draw.text((550, 312), "HS Code", fill=(15, 23, 42))
    draw.text((750, 312), "Qty", fill=(15, 23, 42))
    draw.text((900, 312), "Unit Price", fill=(15, 23, 42))
    draw.text((1050, 312), "Total (EUR)", fill=(15, 23, 42))

    items = [
        ("Industrial CNC Servo Modules Model AX-4", "8471.30.00", "12 Units", "€ 4,000.00", "€ 48,000.00"),
        ("Precision Optical Laser Sensors L-90", "9031.80.80", "20 Units", "€ 2,500.00", "€ 50,000.00"),
        ("Embedded Microcontroller Assemblies", "8542.31.00", "50 Units", "€ 1,010.00", "€ 50,500.00"),
    ]

    y = 360
    for desc, hs, qty, price, total in items:
        draw.text((80, y), desc, fill=(30, 41, 59))
        draw.text((550, y), hs, fill=(51, 65, 85))
        draw.text((750, y), qty, fill=(51, 65, 85))
        draw.text((900, y), price, fill=(51, 65, 85))
        draw.text((1050, y), total, fill=(51, 65, 85))
        draw.line([60, y + 35, width - 60, y + 35], fill=(241, 245, 249), width=1)
        y += 50

    # True Subtotal is 48k + 50k + 50.5k = 148,500 EUR
    # Tampered Grand Total spliced to 248,500 EUR (+100k fraud attempt!)
    draw.line([60, y + 20, width - 60, y + 20], fill=(203, 213, 225), width=2)
    draw.text((750, y + 50), "Subtotal:", fill=(71, 85, 105))
    draw.text((1050, y + 50), "€ 148,500.00", fill=(71, 85, 105))

    # Tampered Total Box: Notice different background artifact and altered number
    tamper_box = [700, y + 90, width - 60, y + 160]
    draw.rectangle(tamper_box, fill=(248, 250, 252), outline=(226, 232, 240), width=2)
    draw.text((730, y + 115), "INVOICE TOTAL:", fill=(15, 23, 42))
    # Spliced altered text
    draw.text((980, y + 115), "€ 248,500.00", fill=(15, 23, 42))

    # Stamp & Signature
    _draw_stamp(draw, 300, y + 260, 65, "VERIFIED", (185, 28, 28), tampered=True)
    draw.text((230, y + 345), "Authorized Signature", fill=(100, 116, 139))
    draw.line([200, y + 340, 420, y + 340], fill=(148, 163, 184), width=2)

    # Save clean/source document
    png_path = out_dir / "Invoice_001.png"
    pdf_path = out_dir / "Invoice_001.pdf"
    img.save(png_path)
    img.save(pdf_path, "PDF", resolution=150.0)

    # Also save an annotated version with red bounding boxes showing forensic detection!
    annotated = img.copy()
    ann_draw = ImageDraw.Draw(annotated)
    # Bounding box on altered total
    ann_draw.rectangle([960, y + 100, 1160, y + 150], outline=(220, 38, 38), width=4)
    ann_draw.text((965, y + 80), "FLAG: ELA Alteration Detected", fill=(220, 38, 38))
    # Bounding box on stamp
    ann_draw.rectangle([220, y + 180, 380, y + 340], outline=(217, 119, 6), width=3)
    ann_draw.text((225, y + 160), "FLAG: Irregular Perimeter", fill=(217, 119, 6))
    annotated.save(out_dir / "Invoice_001_forensic_annotated.png")

    return pdf_path


def generate_bill_of_lading(out_dir: Path) -> Path:
    """Generate Bill_of_Lading_772.pdf (Medium Risk)."""
    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([60, 50, width - 60, 130], fill=(30, 41, 59))
    draw.text((80, 75), "OCEAN BILL OF LADING", fill=(255, 255, 255))
    draw.text((width - 320, 85), "B/L NO: BOL-9921-HK", fill=(203, 213, 225))

    # Shipping Details
    draw.text((70, 170), "Carrier: Pacific Freight Express Lines", fill=(15, 23, 42))
    draw.text((70, 205), "Vessel / Voyage: PACIFIC GLORY / 402W", fill=(71, 85, 105))
    draw.text((70, 240), "Port of Loading: Hong Kong (HKHKG)", fill=(71, 85, 105))
    draw.text((70, 275), "Port of Discharge: Rotterdam (NLRTM)", fill=(71, 85, 105))

    draw.text((width - 450, 170), "Container No: CMAU3381920", fill=(15, 23, 42))
    draw.text((width - 450, 205), "Seal No: ML-880291", fill=(71, 85, 105))
    draw.text((width - 450, 240), "Gross Weight: 18,420 KGS", fill=(71, 85, 105))
    draw.text((width - 450, 275), "Declared Value: $112,000.00 USD", fill=(71, 85, 105))

    draw.line([60, 320, width - 60, 320], fill=(203, 213, 225), width=2)
    _draw_stamp(draw, 900, 600, 60, "CARRIER", (30, 64, 175), tampered=False)

    pdf_path = out_dir / "Bill_of_Lading_772.pdf"
    img.save(out_dir / "Bill_of_Lading_772.png")
    img.save(pdf_path, "PDF", resolution=150.0)
    return pdf_path


def generate_customs_document(out_dir: Path) -> Path:
    """Generate Customs_Dec_409.pdf (Low Risk / Compliant)."""
    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([60, 50, width - 60, 130], fill=(13, 148, 136))
    draw.text((80, 75), "CUSTOMS GOODS IMPORT DECLARATION", fill=(255, 255, 255))
    draw.text((width - 320, 85), "ENTRY REF: CD-44019-SG", fill=(240, 253, 250))

    draw.text((70, 170), "Declarant: Singapore Trade Gateways Pte Ltd", fill=(15, 23, 42))
    draw.text((70, 205), "Country of Origin: Singapore (SG)", fill=(71, 85, 105))
    draw.text((70, 240), "HS Tariff Code: 8473.30.1000", fill=(71, 85, 105))
    draw.text((70, 275), "Customs Value: SGD 45,300.00", fill=(71, 85, 105))

    _draw_stamp(draw, 950, 450, 60, "CUSTOMS", (13, 148, 136), tampered=False)

    pdf_path = out_dir / "Customs_Dec_409.pdf"
    img.save(out_dir / "Customs_Dec_409.png")
    img.save(pdf_path, "PDF", resolution=150.0)
    return pdf_path


if __name__ == "__main__":
    out = Path("data/samples")
    out.mkdir(parents=True, exist_ok=True)
    generate_invoice_001(out)
    generate_bill_of_lading(out)
    generate_customs_document(out)
    print("Generated synthetic trade documents in data/samples/")
