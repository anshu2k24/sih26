# SIH 2026 PS121 — Handwritten Notes OCR & Ingestion Architecture

## 1. Executive Summary

This module implements a production-grade **Handwritten Notes OCR & Intelligent Document Ingestion System** for **Smart India Hackathon 2026 (Problem Statement PS121)**.

### Core Operating Axiom
> **"OCR output is a DRAFT. Human verification makes it TRUSTED DATA."**

The system preserves the original handwritten document image, maintains an immutable provenance record, supports pluggable OCR providers (Mistral OCR / Pixtral Vision, Mock demo provider), extracts domain entities (measurements, dates, tasks, equipment IDs), and provides a side-by-side human review studio.

---

## 2. End-to-End Ingestion Pipeline

```mermaid
flowchart TD
    A["Original Handwritten Document (Photo / Scan)"] --> B["Multi-Layer File Validation<br/>(Magic Bytes, MIME, Size, Dimensions)"]
    B --> C["Object & Local Storage<br/>(SHA-256 Checksum Fingerprinting)"]
    C --> D["Non-Destructive Image Preprocessing<br/>(EXIF Orientation, Contrast Boost, Scaling)"]
    D --> E["Pluggable OCR Engine<br/>(Mistral OCR / Pixtral Vision / Mock)"]
    E --> F["Text Normalization<br/>(UTF-8 NFC, Whitespace, Punctuation)"]
    F --> G["Structured Domain Extraction<br/>(Dates, Measurements, Tasks, Equipment IDs)"]
    G --> H["Draft State: NEEDS_REVIEW<br/>(Preserves raw_ocr_text separately)"]
    H --> I["Side-by-Side Review Studio<br/>(Zoomable Original ↔ Editable Draft)"]
    I --> J["Human Verification Action<br/>(Records verified_by, verified_at, verified_text)"]
    J --> K["Trusted Verified Knowledge Node<br/>(Full Provenance Chain Attached)"]
    K --> L["PostgreSQL FTS Search & Export<br/>(TXT, JSON, Reports)"]
```

---

## 3. Modular OCR Provider Abstraction

The system decouples business logic from specific OCR models via the `OCRProvider` interface:

```mermaid
classDiagram
    class OCRProvider {
        <<interface>>
        +provider_name: str
        +default_model: str
        +extract_text(ocr_input: OCRInput, model: str) OCRResult
        +health_check() bool
    }
    class MistralOCRProvider {
        +api_key: str
        +default_model: str
        +extract_text()
        +health_check()
    }
    class MockOCRProvider {
        +simulated_delay_ms: int
        +extract_text()
        +health_check()
    }
    class OCRService {
        +preprocessor: ImagePreprocessor
        +provider: OCRProvider
        +process_image() OCRResult
        +health_check()
    }

    OCRProvider <|-- MistralOCRProvider
    OCRProvider <|-- MockOCRProvider
    OCRService o-- OCRProvider
```

### Supported Providers:
1. **Mistral AI (`mistral`)**:
   - `mistral-ocr-latest`: Dedicated document and handwriting OCR API.
   - `pixtral-12b-2409`: Multimodal vision LLM providing resilient transcriptions for challenging handwriting.
2. **Mock Provider (`mock`)**:
   - Deterministic offline provider for CI tests, development, and offline demo environments (`OCR_PROVIDER=mock`).

---

## 4. Provenance & Auditability Model

Every verified note maintains a four-tier traceable chain:

1. **Source Document**: Preserved file at `data/notes_images/` with SHA-256 hash.
2. **OCR Run History**: Immutable record in `ocr_runs` table tracking attempt count, provider, model, latency, and machine draft.
3. **Machine Draft**: `raw_ocr_text` preserved permanently and never overwritten.
4. **Human Verification**: `verified_text`, `verified_by` (User ID / Profile), and `verified_at` timestamp.

---

## 5. Security & RBAC Matrix

| Role | View Notes | Upload & OCR | Edit Draft | Verify & Promote | Delete Note |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ADMIN** | Yes | Yes | Yes | Yes | Yes |
| **DRILLING_ENGINEER** | Yes | Yes | Yes | Yes | Yes |
| **OPERATIONS_ENGINEER** | Yes | Yes | Yes | Yes | Yes |
| **ANALYST** | Yes | Yes | Yes | No | No |
| **VIEWER** | Yes | No | No | No | No |
