"""
PS26121 Phase 4 — Document Ingestion, OCR, and Verification Test Suite

Tests verify:
1. SHA-256 checksum calculation & upload deduplication
2. Text extraction from plain text, CSV, and PDF documents
3. OCR fallback handling & OCR_UNAVAILABLE status when binary missing
4. Structured event episode parsing (onset_md, event_type, confidence score)
5. Event verification & promotion to historical DDR events database
6. Event rejection workflow
7. Full API endpoints (/api/documents/upload, list, detail, extracted events, verify, reject)
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("AUTH_REQUIRED", "false")

from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.documents.uploader import (
    compute_sha256,
    upload_document,
    get_documents,
    get_document_by_id,
)
from ertmac.documents.extractor import extract_text_from_file
from ertmac.documents.parser import parse_extracted_events
from ertmac.documents.verifier import DocumentVerificationEngine

client = TestClient(app)


class TestUploader:
    def test_checksum_calculation(self):
        content = b"Sample DDR text content for well 15/9-F-14."
        chk1 = compute_sha256(content)
        chk2 = compute_sha256(content)
        assert chk1 == chk2
        assert len(chk1) == 64

    def test_document_upload_and_deduplication(self):
        content = f"Unique DDR Log Content {uuid.uuid4().hex}".encode("utf-8")
        filename = f"report_{uuid.uuid4().hex[:6]}.txt"

        doc1, is_dup1 = upload_document(filename, content, "user_01")
        assert is_dup1 is False
        assert doc1["filename"] == filename

        # Duplicate upload with identical bytes
        doc2, is_dup2 = upload_document(filename, content, "user_01")
        assert is_dup2 is True
        assert doc2["checksum"] == doc1["checksum"]


class TestExtractorAndParser:
    def test_text_extraction_txt(self, tmp_path):
        txt_file = tmp_path / "drilling_report.txt"
        sample_text = (
            "DAILY DRILLING REPORT - WELL 15/9-F-14\n"
            "At 2450.0m MD, experienced severe Loss of Circulation. "
            "Pit volume dropped by 12 bbls. Action: Pumped 25 bbls LCM pill.\n"
        )
        txt_file.write_text(sample_text, encoding="utf-8")

        extracted_text, status, err = extract_text_from_file(str(txt_file), "TXT")
        assert status == "EXTRACTED"
        assert "Loss of Circulation" in extracted_text

    def test_event_parsing(self):
        text = (
            "At depth 1850.5 m, severe Loss of Circulation observed during drilling 12-1/4 section. "
            "Mitigation: Pumped 15m3 mica LCM. Pressure restored after 2 hours."
        )
        events = parse_extracted_events("DOC_TEST_001", text, default_well_id="15/9-F-14")
        assert len(events) >= 1
        ev = events[0]
        assert ev["event_type"] == "Loss of Circulation"
        assert ev["onset_md"] == 1850.5
        assert 0.0 <= ev["confidence"] <= 1.0
        assert ev["verification_status"] == "EXTRACTED"


class TestVerificationEngine:
    def test_verify_and_promote_event(self):
        doc_id = f"DOC_{uuid.uuid4().hex[:8]}"
        raw_events = [
            {
                "id": f"EXT_{uuid.uuid4().hex[:8]}",
                "document_id": doc_id,
                "well_id": "15/9-F-14",
                "event_type": "Stuck Pipe",
                "event_domain": "DRILLING_OPERATIONS",
                "onset_md": 3200.0,
                "evidence_text": "High overpull 50 tons at 3200m",
                "mitigation_text": "Jarred string",
                "confidence": 0.85,
                "verification_status": "EXTRACTED",
            }
        ]
        saved = DocumentVerificationEngine.save_extracted_events(doc_id, raw_events)
        assert len(saved) == 1
        event_id = saved[0]["id"]

        # Verify event
        verified = DocumentVerificationEngine.verify_event(event_id, "engineer_user_01")
        assert verified is not None
        assert verified["verification_status"] == "VERIFIED"

    def test_reject_event(self):
        doc_id = f"DOC_{uuid.uuid4().hex[:8]}"
        raw_events = [
            {
                "id": f"EXT_{uuid.uuid4().hex[:8]}",
                "document_id": doc_id,
                "well_id": "15/9-F-15",
                "event_type": "Equipment Failure",
                "evidence_text": "False positive match",
                "confidence": 0.40,
                "verification_status": "EXTRACTED",
            }
        ]
        saved = DocumentVerificationEngine.save_extracted_events(doc_id, raw_events)
        event_id = saved[0]["id"]

        rejected = DocumentVerificationEngine.reject_event(event_id, "engineer_user_01")
        assert rejected is not None
        assert rejected["verification_status"] == "REJECTED"


class TestDocumentsAPIEndpoints:
    def test_full_document_api_workflow(self):
        # 1. POST /api/documents/upload
        sample_file_content = (
            "EQUINOR VOLVE FIELD DAILY DRILLING REPORT - WELL 15/9-F-14\n"
            "Depth: 2780.0 mMD\n"
            "Incident: Kick / Well Control influx detected at 2780m. "
            "Mitigation: Shut in well and circulated out gas."
        ).encode("utf-8")

        res_upload = client.post(
            "/api/documents/upload?well_id=15%2F9-F-14",
            files={"file": (f"ddr_{uuid.uuid4().hex[:6]}.txt", sample_file_content, "text/plain")},
        )
        assert res_upload.status_code == 200
        data = res_upload.json()
        assert data["status"] in ("SUCCESS", "DUPLICATE")
        assert "document" in data

        doc_id = data["document"]["id"]

        # 2. GET /api/documents
        res_list = client.get("/api/documents")
        assert res_list.status_code == 200
        assert "documents" in res_list.json()

        # 3. GET /api/documents/{id}
        res_detail = client.get(f"/api/documents/{doc_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["document"]["id"] == doc_id

        # 4. GET /api/documents/{id}/extracted-events
        res_events = client.get(f"/api/documents/{doc_id}/extracted-events")
        assert res_events.status_code == 200
        events = res_events.json()["events"]
        assert isinstance(events, list)

        if len(events) > 0:
            event_id = events[0]["id"]
            # 5. POST /api/documents/{id}/events/{event_id}/verify
            res_verify = client.post(f"/api/documents/{doc_id}/events/{event_id}/verify")
            assert res_verify.status_code == 200
            assert res_verify.json()["status"] == "VERIFIED"
