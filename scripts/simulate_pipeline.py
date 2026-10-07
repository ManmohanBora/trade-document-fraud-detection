"""
Live pipeline simulation runner.

Executes an interactive end-to-end multi-modal analysis cycle
with staged real-time logging, realistic timing, and terminal UI.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# ANSI Color Codes for terminal formatting
NAVY = "\033[38;2;15;23;42m"
TEAL = "\033[38;2;13;148;136m"
AMBER = "\033[38;2;217;119;6m"
RED = "\033[38;2;220;38;38m"
GREEN = "\033[38;2;22;163;74m"
GRAY = "\033[38;2;100;116;139m"
BOLD = "\033[1m"
RESET = "\033[0m"


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def log_step(step_num: int, title: str, details: str = "") -> None:
    print(f"\n{BOLD}{TEAL}[{step_num}/6] {title}{RESET}")
    if details:
        print(f"  {GRAY}{details}{RESET}")


def log_substep(branch: str, message: str, flag: str | None = None) -> None:
    flag_str = f" {AMBER}[FLAG: {flag}]{RESET}" if flag else ""
    print(f"  {GRAY}|- [{branch}]{RESET} {message}{flag_str}")


async def run_simulation(doc_path: Path) -> None:
    filename = doc_path.name
    print(f"\n{BOLD}{'=' * 70}")
    print(f"  MULTI-MODAL AI AUDIT PIPELINE - RUNNER SIMULATION")
    print(f"  Target File: {filename}")
    print(f"{'=' * 70}{RESET}")

    # Stage 1: Upload & FastAPI
    log_step(1, "FASTAPI DOCUMENT INGESTION", "Payload received via POST /api/v1/documents/upload")
    await asyncio.sleep(0.4)
    file_size_kb = doc_path.stat().st_size / 1024 if doc_path.exists() else 184.2
    print(f"  {GREEN}[OK] Validated MIME: application/pdf | Size: {file_size_kb:.1f} KB | Document ID: 4f9e1a88-90c1{RESET}")

    # Stage 2: OCR & Preprocessing
    log_step(2, "OCR & PREPROCESSING ENGINE", "Converting PDF to 300 DPI raster, contrast normalization")
    await asyncio.sleep(0.6)
    print(f"  {GREEN}[OK] OCR Engine: Tesseract v5.3 | Mean Confidence: 94.2% | Text Tokens: 384{RESET}")

    # Stage 3: Parallel Branches
    log_step(3, "PARALLEL DUAL-BRANCH MULTIMODAL INFERENCE", "Running Image Analytics and NLP Understanding concurrently")
    await asyncio.sleep(0.7)

    # Branch A: Image Analytics
    print(f"\n  {BOLD}--- Branch A: Image Analytics (OpenCV · YOLO · ResNet) ---{RESET}")
    log_substep("OpenCV-ELA", "Error Level Analysis executed on 1240x1754 matrix")
    log_substep("OpenCV-ELA", "Compression differential spike detected at (x:960, y:815)", flag="ALTERATION")
    log_substep("YOLOv8-Stamps", "Identified 1 official stamp perimeter")
    log_substep("ResNet-Sim", "Stamp cosine similarity score: 0.61 vs reference registry", flag="STAMP MISMATCH")
    log_substep("Layout-Morph", "Whitespace skew: 14.2% | Grid column misalignment: 18.5%", flag="UNUSUAL LAYOUT")

    await asyncio.sleep(0.5)

    # Branch B: NLP Document Understanding
    print(f"\n  {BOLD}--- Branch B: NLP / LayoutLMv3 Transformers ---{RESET}")
    log_substep("LayoutLMv3", "Spatial token classification completed across 4 bounding boxes")
    log_substep("EntityExtractor", "Invoice No: INV-89104-DE | Currency: EUR | HS Code: 8471.30.00")
    log_substep("CrossValidator", "Sum of line items: EUR 148,500.00 | Stated Total: EUR 248,500.00", flag="AMOUNT INCONSISTENCY")
    log_substep("EntityValidator", "Container ID MSCU7829104 validated (ISO 6346 compliant)")

    # Stage 4: Fusion
    log_step(4, "MULTIMODAL FEATURE FUSION", "Correlating spatial textual claims with visual pixel anomalies")
    await asyncio.sleep(0.5)
    print(f"  {AMBER}* Cross-Modal Flag: Visual ELA alteration matches line-item amount anomaly!{RESET}")
    print(f"  {AMBER}* Cross-Modal Flag: Unregistered stamp seal paired with high financial exposure{RESET}")

    # Stage 5: Risk Scorer
    log_step(5, "EXPLAINABLE RISK SCORING ENGINE", "Evaluating weighted evidence contributions")
    await asyncio.sleep(0.4)
    print(f"  {GRAY}|- Visual alteration penalty: +35.0 pts{RESET}")
    print(f"  {GRAY}|- Financial amount inconsistency: +25.0 pts{RESET}")
    print(f"  {GRAY}|- Layout morphology anomaly: +18.0 pts{RESET}")

    # Stage 6: Persistence & Result
    log_step(6, "AUDIT PERSISTENCE & HUMAN AUDITOR DISPATCH", "Committed to PostgreSQL audit_records table")
    await asyncio.sleep(0.3)

    # Final Audited Result Card Output
    border_len = 68
    print(f"\n{BOLD}+{'-' * border_len}+")
    print(f"| AUDIT RESULT CARD (Streamlit & API Record){' ' * (border_len - 43)}|")
    print(f"+{'-' * border_len}+")
    print(f"| Document:    {BOLD}{filename}{RESET}{' ' * (border_len - 15 - len(filename))}|")
    print(f"| Risk Score:  {BOLD}{AMBER}78/100{RESET}{' ' * (border_len - 19)}|")
    print(f"| Risk Level:  {BOLD}{AMBER}High{RESET}{' ' * (border_len - 17)}|")
    print(f"| Reasons:     {BOLD}Suspicious visual alteration · Amount inconsistency ·{RESET}  |")
    print(f"|              {BOLD}Unusual document layout{RESET}{' ' * (border_len - 38)}|")
    print(f"+{'-' * border_len}+")
    print(f"| {TEAL}[NOTICE] AI-generated risk indicator—not proof of fraud.{RESET}{' ' * (border_len - 58)}|")
    print(f"| {TEAL}         Final decision remains with the human auditor.{RESET}{' ' * (border_len - 56)}|")
    print(f"+{'-' * border_len}+{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Modal AI Audit Pipeline Simulation")
    parser.add_argument(
        "--document",
        type=str,
        default="data/samples/Invoice_001.pdf",
        help="Path to trade document for analysis",
    )
    args = parser.parse_args()
    asyncio.run(run_simulation(Path(args.document)))
