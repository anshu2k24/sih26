"""
PS121 Handwritten Notes OCR — API Endpoints Test Suite
Tests FastAPI router endpoints: Upload, Detail, Draft Save, Verification, Runs, Metrics, Export, and Image streaming.
"""

import io
import os
import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.ocr.providers.mock import MockOCRProvider
from ertmac.notes.service import global_handwritten_notes_service
from tests.test_file_validation import create_test_image


@pytest.fixture
def client():
    # Configure mock OCR provider for deterministic test runs
    global_handwritten_notes_service.ocr_service.provider = MockOCRProvider(simulated_delay_ms=0)
    with TestClient(app) as test_client:
        yield test_client


class TestNotesAPI:

    def test_upload_and_verify_flow(self, client):
        img_bytes = create_test_image("JPEG", (600, 400), color="green")
        
        # 1. Upload Note via POST /api/v1/notes/ocr
        files = {"file": ("handwritten_drilling_log.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        data = {"title": "Field Inspection Log #101"}

        resp = client.post("/api/v1/notes/ocr", files=files, data=data)
        assert resp.status_code == 200, resp.text
        json_res = resp.json()
        assert json_res["success"] is True
        assert json_res["status"] == "NEEDS_REVIEW"
        note = json_res["note"]
        note_id = note["id"]
        assert note["title"] == "Field Inspection Log #101"
        assert note["ocr_status"] == "COMPLETED"

        # 2. Get Note Details via GET /api/v1/notes/{id}
        detail_resp = client.get(f"/api/v1/notes/{note_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["note"]["id"] == note_id
        assert len(detail_data["ocr_runs"]) >= 1

        # 3. Save Draft via PATCH /api/v1/notes/{id}
        draft_resp = client.patch(
            f"/api/v1/notes/{note_id}",
            json={"title": "Updated Draft Title", "verified_text": "Draft correction: Pressure was 160 bar."},
        )
        assert draft_resp.status_code == 200
        assert draft_resp.json()["note"]["title"] == "Updated Draft Title"
        assert draft_resp.json()["note"]["verified_text"] == "Draft correction: Pressure was 160 bar."

        # 4. Verify Note via POST /api/v1/notes/{id}/verify
        verify_resp = client.post(
            f"/api/v1/notes/{note_id}/verify",
            json={
                "title": "Final Verified Inspection #101",
                "verified_text": "FINAL VERIFIED: Pressure checked at 160 bar. Valve replaced.",
            },
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["note"]["verification_status"] == "VERIFIED"

        # 5. List Notes via GET /api/v1/notes
        list_resp = client.get("/api/v1/notes")
        assert list_resp.status_code == 200
        assert list_resp.json()["count"] >= 1

        # 6. Get Metrics via GET /api/v1/notes/metrics
        metrics_resp = client.get("/api/v1/notes/metrics")
        assert metrics_resp.status_code == 200
        metrics = metrics_resp.json()
        assert metrics["total_notes"] >= 1

        # 7. Get OCR Run History via GET /api/v1/notes/{id}/ocr-runs
        runs_resp = client.get(f"/api/v1/notes/{note_id}/ocr-runs")
        assert runs_resp.status_code == 200
        assert runs_resp.json()["count"] >= 1

        # 8. Export Note as JSON
        export_resp = client.get(f"/api/v1/notes/{note_id}/export?format=json")
        assert export_resp.status_code == 200
        assert "application/json" in export_resp.headers.get("content-type", "")

        # 9. Delete Note via DELETE /api/v1/notes/{id}
        del_resp = client.delete(f"/api/v1/notes/{note_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "DELETED"
