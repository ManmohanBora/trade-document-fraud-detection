# Pipeline Process Documentation
## Multi-Modal AI Pipeline for Trade Document Fraud Detection & Compliance Auditing

> **AI-generated risk indicator — not proof of fraud. Final decision remains with the human auditor.**

---

## Table of Contents

1. [Pipeline Overview](#pipeline-overview)
2. [Stage 1: Document Upload](#stage-1-document-upload)
3. [Stage 2: OCR + Preprocessing](#stage-2-ocr--preprocessing)
4. [Stage 3A: Image Analytics Branch](#stage-3a-image-analytics-branch)
5. [Stage 3B: NLP / Document Understanding Branch](#stage-3b-nlp--document-understanding-branch)
6. [Stage 4: Multimodal Feature Fusion](#stage-4-multimodal-feature-fusion)
7. [Stage 5: Risk Assessment](#stage-5-risk-assessment)
8. [Stage 6: Human Audit Recommendation](#stage-6-human-audit-recommendation)
9. [Stage 7: Storage & Visualization](#stage-7-storage--visualization)
10. [Data Flow Diagram](#data-flow-diagram)
11. [Technology Justification](#technology-justification)
12. [Ethical Design Principles](#ethical-design-principles)

---

## Pipeline Overview

```
┌──────────────┐    ┌──────────┐    ┌─────────────────┐
│   Trade      │───▶│ FastAPI  │───▶│ OCR +           │
│   Documents  │    │ Upload   │    │ Preprocessing   │
└──────────────┘    └──────────┘    └────────┬────────┘
                                             │
                                    ┌────────┴────────┐
                                    ▼                  ▼
                           ┌────────────────┐  ┌────────────────────┐
                           │ Image          │  │ NLP / Document     │
                           │ Analytics      │  │ Understanding      │
                           │                │  │                    │
                           │ OpenCV · YOLO  │  │ OCR · LayoutLMv3   │
                           │ ResNet         │  │ Transformers       │
                           └───────┬────────┘  └────────┬───────────┘
                                   │                     │
                                   └──────────┬──────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │ Multimodal Feature   │
                                   │ Fusion               │
                                   └──────────┬──────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │ Risk Assessment      │
                                   └──────────┬──────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │ Human Audit          │
                                   │ Recommendation       │
                                   └──────────┬──────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                    ▼
                           ┌────────────────┐  ┌────────────────────┐
                           │ PostgreSQL     │  │ Streamlit + Plotly  │
                           │ Audit Records  │  │ Dashboard           │
                           └────────────────┘  └────────────────────┘
```

---

## Stage 1: Document Upload

**Module:** `api/routes/documents.py`
**Technology:** FastAPI, Pydantic

### Process

1. User uploads a trade document (PDF or image) via the REST API
2. File is validated:
   - **Type check:** Only `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff` accepted
   - **Size check:** Maximum 50 MB (configurable)
   - **Filename sanitization:** UUID-based renaming prevents path traversal
3. File is persisted to `data/uploads/{document_id}.{ext}`
4. A `DocumentMetadata` record is created with:
   - Unique document ID (UUID v4)
   - Original filename
   - File path, size, MIME type
   - Upload timestamp (UTC)
5. Document is queued for pipeline processing

### Input → Output

| Input                     | Output                |
|---------------------------|-----------------------|
| Multipart file upload     | `DocumentMetadata`    |
| Content-type header       | Queued processing job |

---

## Stage 2: OCR + Preprocessing

**Module:** `preprocessing/ocr_engine.py`
**Technology:** Tesseract / EasyOCR, pdf2image, Pillow

### Process

1. **PDF Conversion:** Multi-page PDFs are converted to individual page images at configured DPI (default: 300)
2. **Image Preprocessing:**
   - Grayscale conversion
   - Contrast enhancement (1.5× via `ImageEnhance`)
   - Sharpening filter
3. **Text Extraction:**
   - Full-text extraction for downstream NLP
   - Word-level bounding boxes with confidence scores
4. **Quality Assessment:**
   - Average OCR confidence computed across all words
   - Low-confidence regions flagged for downstream attention

### Input → Output

| Input              | Output           |
|--------------------|------------------|
| `DocumentMetadata` | `OCRResult`      |
|                    | ├ `full_text`    |
|                    | ├ `word_boxes[]` |
|                    | ├ `page_images[]`|
|                    | └ `avg_confidence`|

### Design Decision
Two OCR backends (Tesseract and EasyOCR) are supported via a strategy pattern. Tesseract is the default for speed; EasyOCR provides better multilingual support. The engine is selected via the `OCR_ENGINE` environment variable.

---

## Stage 3A: Image Analytics Branch

**Module:** `image_analytics/`
**Technology:** OpenCV, YOLO, ResNet

### Sub-Components

#### 1. Manipulation Detection (`manipulation_detector.py`)
- **Error Level Analysis (ELA):** Re-compresses the image at a known quality level and measures pixel-level differences. Tampered regions that have undergone fewer compression cycles show higher error levels.
- **Noise Inconsistency Analysis:** Divides the image into blocks and measures local noise variance via Laplacian operators. Spliced content typically has a different noise signature than the surrounding document.

#### 2. Stamp/Seal Detection (`stamp_seal_detector.py`)
- **Primary:** YOLO object detection trained on stamp/seal regions
- **Fallback:** Hough Circle Transform for circular stamps when YOLO model is unavailable
- **Classification:** Detected regions are classified as "official_stamp", "company_seal", or "unknown"

#### 3. Layout Analysis (`layout_analyzer.py`)
- Morphological text block detection (binary threshold + closing operations)
- Positional region classification (header, body, table, footer)
- Alignment consistency scoring (left-margin standard deviation)
- Whitespace ratio computation

### Input → Output

| Input           | Output           |
|-----------------|------------------|
| `page_images[]` | `ImageEvidence`  |
|                 | ├ signature detection     |
|                 | ├ stamp/seal detection    |
|                 | ├ logo verification       |
|                 | ├ layout anomaly score    |
|                 | └ manipulation regions    |

---

## Stage 3B: NLP / Document Understanding Branch

**Module:** `nlp/`
**Technology:** LayoutLMv3, Transformers, regex patterns

### Sub-Components

#### 1. Field Extraction (`field_extractor.py`)
Regex-based extraction of structured fields:
- **Invoice number:** `INV-2024-001`, `Invoice No. 12345`
- **Amount + Currency:** `$1,234.56 USD`, `Total: 50,000 EUR`
- **Date:** `2024-01-15`, `Jan 15, 2024`, `15/01/2024`
- **HS Code:** `8471.30.0100` (6–10 digit harmonized system code)
- **Container Number:** `ABCU1234567` (ISO 6346 format)
- **Bill of Lading Number**

#### 2. Layout-Aware Understanding (`layout_lm.py`)
- LayoutLMv3 processes text tokens with their 2D positional embeddings
- Captures spatial relationships (e.g., "amount" appearing next to a table cell vs. a header)
- Produces token-level classifications and layout feature vectors

#### 3. Entity Validation (`entity_validator.py`)
Cross-field consistency checks:
- **HS Code:** Chapter range (01–99), digit count (6–10)
- **Container Number:** ISO 6346 checksum, owner code, equipment category
- **Amount:** Positive, within plausible range
- **Date:** Not future, not pre-2000
- **Buyer ≠ Seller:** Identity check

### Input → Output

| Input            | Output           |
|------------------|------------------|
| `full_text`      | `TextEvidence`   |
| `word_boxes[]`   | ├ extracted fields        |
|                  | ├ field confidence        |
|                  | ├ layout features         |
|                  | └ anomaly list            |

---

## Stage 4: Multimodal Feature Fusion

**Module:** `fusion/feature_combiner.py`

### Process

The fusion stage combines evidence from both analysis branches and generates **cross-modal flags** — correlations between visual and textual anomalies that neither branch could detect alone:

| Cross-Modal Flag | Trigger Condition |
|------------------|-------------------|
| Visual manipulation + financial data | Manipulation detected + amount field present |
| Missing stamp on numbered invoice | No stamp/seal + invoice number extracted |
| Layout + text anomaly correlation | Layout anomaly score > 0.5 + text anomalies present |
| Unverified logo on high-value doc | Logo match < 50% + amount > $100,000 |
| Missing signature on formal doc | No signature + invoice number present |

### Input → Output

| Input            | Output              |
|------------------|---------------------|
| `ImageEvidence`  | `FusedEvidence`     |
| `TextEvidence`   | ├ combined evidence          |
|                  | ├ cross-modal flags          |
|                  | └ fusion confidence          |

---

## Stage 5: Risk Assessment

**Module:** `risk/scorer.py`

### Scoring Methodology

The risk score (0–100) is a **weighted, explainable** composite:

```
risk_score = Σ(visual_signals × 0.4) + Σ(textual_signals × 0.4) + Σ(cross_modal_signals × 0.5) + base_penalty
```

#### Signal Point Values

| Signal Category | Signal | Max Points |
|-----------------|--------|------------|
| **Visual** | Manipulation detected | 25 |
| **Visual** | Layout anomaly | 15 |
| **Visual** | Missing signature | 5 |
| **Visual** | Missing stamp/seal | 5 |
| **Visual** | Logo mismatch | 10 |
| **Textual** | Field anomalies | 25 |
| **Textual** | Missing critical fields | 15 |
| **Cross-Modal** | Each cross-modal flag | 10 |

#### Risk Levels

| Score Range | Level | Action |
|-------------|-------|--------|
| 70–100 | **High** | Priority review by senior auditor |
| 40–69 | **Medium** | Standard audit review |
| 0–39 | **Low** | Standard processing, spot-check |

**Every point is traceable** — the `ScoreContribution` dataclass records source, points, reason, and category for each contribution.

---

## Stage 6: Human Audit Recommendation

The system generates a natural-language recommendation based on risk level:

- **High Risk:** "PRIORITY REVIEW RECOMMENDED. Multiple risk indicators detected. This document should be reviewed by a senior compliance auditor before processing."
- **Medium Risk:** "STANDARD REVIEW RECOMMENDED. Some risk indicators present."
- **Low Risk:** "LOW RISK — no immediate concerns detected. Periodic spot-check recommended."

> ⚠️ **The system never determines fraud.** It generates risk indicators to assist human auditors. The `CAVEAT` string is attached to every audit result:
> *"AI-generated risk indicator — not proof of fraud. Final decision remains with the human auditor."*

---

## Stage 7: Storage & Visualization

### PostgreSQL Audit Records (`db/models.py`)

Each `AuditRecord` stores:
- Document metadata (ID, filename, size, MIME type)
- Risk assessment (score, level, reasons, recommendation)
- Extracted fields (invoice number, amount, currency, HS code, etc.)
- Semi-structured evidence (image/text evidence as JSONB)
- Human review tracking (reviewer, decision, notes, timestamp)

**Indexes:** `risk_level`, `created_at`, `document_filename`, `audit_id`, `document_id`

### Streamlit + Plotly Dashboard

- Real-time audit result display
- Risk distribution charts
- Document drill-down with evidence details
- Filtering by risk level, date range, document type

---

## Data Flow Diagram

```
User Upload (PDF/Image)
        │
        ▼
   ┌─────────┐
   │ FastAPI  │──── Validation ──── Rejection (422)
   │ Upload   │
   └────┬─────┘
        │ DocumentMetadata
        ▼
   ┌──────────────────┐
   │ OCR +            │
   │ Preprocessing    │──── OCRResult
   └────┬──────┬──────┘
        │      │
   ┌────▼──┐ ┌─▼────────────────┐
   │ Image │ │ NLP / Document   │
   │ Anal. │ │ Understanding    │
   └───┬───┘ └────────┬─────────┘
       │ ImageEvidence │ TextEvidence
       └──────┬────────┘
              ▼
   ┌─────────────────────┐
   │ Multimodal Fusion   │──── FusedEvidence + Cross-Modal Flags
   └──────────┬──────────┘
              ▼
   ┌─────────────────────┐
   │ Risk Assessment     │──── RiskAssessment (score, level, reasons)
   └──────────┬──────────┘
              ▼
   ┌─────────────────────┐
   │ Human Audit         │──── Recommendation text
   │ Recommendation      │
   └──────────┬──────────┘
              │
      ┌───────┴───────┐
      ▼               ▼
 ┌──────────┐  ┌─────────────┐
 │PostgreSQL│  │ Streamlit   │
 │ Audit DB │  │ Dashboard   │
 └──────────┘  └─────────────┘
```

---

## Technology Justification

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **FastAPI** | API server | Async-native, Pydantic validation, auto-generated OpenAPI docs |
| **Tesseract/EasyOCR** | Text extraction | Industry-standard OCR; dual-engine for flexibility |
| **OpenCV** | Image processing | De facto standard for CV; ELA, morphology, Hough transforms |
| **YOLO** | Object detection | Real-time stamp/seal detection; proven accuracy |
| **ResNet** | Feature extraction | Transfer learning for stamp classification |
| **LayoutLMv3** | Layout understanding | State-of-the-art for document AI; captures text + position |
| **PostgreSQL** | Audit storage | JSONB for semi-structured data; enterprise-grade reliability |
| **SQLAlchemy** | ORM | Async support; Alembic migrations; type-safe queries |
| **Streamlit** | Dashboard | Rapid prototyping; built-in Plotly integration |
| **Docker** | Containerization | Reproducible environments; cloud-ready deployment |

---

## Ethical Design Principles

1. **No autonomous fraud determination.** The system is an advisory tool. It generates risk indicators, not verdicts.
2. **Explainable scoring.** Every point in the risk score maps to a specific, documented evidence signal.
3. **Human-in-the-loop.** All medium and high-risk documents are flagged for human review. The system cannot override or bypass an auditor.
4. **Transparent caveats.** Every audit result includes a visible disclaimer.
5. **No fabricated metrics.** The system does not claim accuracy percentages or false-positive rates without rigorous evaluation on representative data.
