# SIH 2026 PS121 — Handwritten Notes OCR API Reference

Base Endpoint: `/api/v1/notes`

---

## 1. Upload & OCR Ingestion
`POST /api/v1/notes/ocr`

Uploads an image, validates magic bytes and resolution, saves original, runs OCR, and extracts structured entities.

### Request: `multipart/form-data`
- `file` (File, required): Image file (JPEG, PNG, WEBP, HEIC, PDF; max 25MB)
- `title` (string, optional): Title override
- `model` (string, optional): OCR model identifier (`mistral-ocr-latest`, `pixtral-12b-2409`, `mock`)

### Response (`200 OK`):
```json
{
  "success": true,
  "status": "NEEDS_REVIEW",
  "note": {
    "id": "c7a8b412-98e3-4d6b-8012-38e534f9a012",
    "title": "Drilling Log — Shift Handover Note",
    "raw_ocr_text": "...",
    "verified_text": "...",
    "source": "handwritten",
    "source_file_id": "file_8f7b2a...",
    "storage_path": "data/notes_images/c7a8b412_8f7b2a12.jpg",
    "public_url": "/api/v1/notes/images/c7a8b412_8f7b2a12.jpg",
    "ocr_status": "COMPLETED",
    "verification_status": "NEEDS_REVIEW",
    "confidence": 0.94,
    "structured_data": {
      "title": "Drilling Log — Shift Handover Note",
      "date": "12/08/2026",
      "measurements": [
        { "parameter": "temperature", "value": "84 °C", "numeric_value": 84.0, "unit": "°C" },
        { "parameter": "pressure", "value": "185 bar", "numeric_value": 185.0, "unit": "bar" }
      ],
      "tasks": ["Replace valve seal on HP mud pump #2"],
      "observations": ["Mud temperature rose from 68°C to 84°C at 3,142m MD"],
      "tags": ["Drilling", "Maintenance"]
    }
  }
}
```

---

## 2. List Notes
`GET /api/v1/notes`

### Query Parameters:
- `limit` (integer, default 50): Number of records
- `offset` (integer, default 0): Offset index
- `status` (string, optional): `NEEDS_REVIEW`, `VERIFIED`, `FAILED`, `PROCESSING`
- `q` (string, optional): Search keyword

---

## 3. Get Note Details & Provenance
`GET /api/v1/notes/{note_id}`

Returns note details, structured data, OCR run history, and provenance metadata.

---

## 4. Save Draft Edits
`PATCH /api/v1/notes/{note_id}`

Saves reviewer's draft corrections without promoting to verified status.

### Request Body:
```json
{
  "title": "Updated Shift Log Title",
  "verified_text": "Corrected transcribed text..."
}
```

---

## 5. Verify & Promote Note
`POST /api/v1/notes/{note_id}/verify`

Marks note as verified trusted data, records verifier ID, updates structured entities, and preserves raw OCR text separately.

### Request Body:
```json
{
  "title": "Final Verified Note Title",
  "verified_text": "Verified operational text..."
}
```

---

## 6. Retry OCR Run
`POST /api/v1/notes/{note_id}/retry`

Re-executes OCR on the stored original document and appends a new run attempt record.

---

## 7. Export Note
`GET /api/v1/notes/{note_id}/export?format=json|txt`

Exports verified note in formatted plain text or structured JSON.

---

## 8. Dashboard Metrics
`GET /api/v1/notes/metrics`

Returns live counts:
```json
{
  "total_notes": 48,
  "processing": 1,
  "needs_review": 6,
  "verified": 39,
  "failed": 2,
  "verification_rate_pct": 81.3,
  "active_provider": "mistral",
  "active_model": "mistral-ocr-latest"
}
```
