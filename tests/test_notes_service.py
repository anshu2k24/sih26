"""
PS121 Handwritten Notes OCR — Notes Service Test Suite
Tests complete lifecycle: Ingestion, Idempotency, Normalization, Entity Extraction, Human Verification, Retries, Provenance, and Export.
"""

import pytest
import io
import json
import asyncio
from PIL import Image
from ertmac.ocr.providers.mock import MockOCRProvider
from ertmac.ocr.service import OCRService
from ertmac.notes.repository import NoteRepository
from ertmac.notes.storage import NoteStorageManager
from ertmac.notes.service import HandwrittenNotesService
from ertmac.notes.normalizer import TextNormalizer
from ertmac.notes.extractor import StructuredExtractor
from tests.test_file_validation import create_test_image


class TestNotesService:

    @pytest.fixture
    def test_service(self, tmp_path):
        mock_provider = MockOCRProvider(simulated_delay_ms=0)
        ocr_service = OCRService(provider=mock_provider)
        repo = NoteRepository()
        storage = NoteStorageManager(base_dir=tmp_path / "notes_storage")
        return HandwrittenNotesService(ocr_service=ocr_service, repository=repo, storage=storage)

    def test_text_normalizer(self):
        raw = "Line 1 with spaces   \r\nLine 2 with \u2018smart quotes\u2019 and \u201cdouble\u201d\n\n\n\nLine 3"
        norm = TextNormalizer.normalize(raw)
        assert "Line 1 with spaces" in norm
        assert "'smart quotes'" in norm
        assert '"double"' in norm
        assert "\r" not in norm
        assert "\n\n\n" not in norm

    def test_structured_extractor(self):
        sample = (
            "DRILLING SHIFT REPORT\n"
            "Date: 12/08/2026 | Time: 14:30 HRS\n"
            "Asset ID: RIG-SLOT-04 | Supervisor: E. Hansen\n\n"
            "Observations:\n"
            "- High vibration on mud pump #2 recorded at 7.2 mm/s\n"
            "- Standpipe Pressure steady at 185 bar with 2400 L/min flow rate\n"
            "- Temperature: 84°C at 3142m MD\n\n"
            "Actions:\n"
            "- Replace valve seal on pump #2\n"
            "- Follow up tomorrow at shift change"
        )
        extracted = StructuredExtractor.extract_structured(sample)
        assert extracted["date"] == "12/08/2026"
        assert len(extracted["times"]) > 0
        assert len(extracted["measurements"]) >= 3
        assert len(extracted["tasks"]) >= 1
        assert len(extracted["observations"]) >= 1
        assert "Drilling" in extracted["tags"] or "Maintenance" in extracted["tags"]

    def test_full_note_ingestion_lifecycle(self, test_service):
        async def _run():
            img_bytes = create_test_image("JPEG", (600, 450), color="blue")
            
            # 1. Ingest Note
            res = await test_service.ingest_handwritten_note(
                file_bytes=img_bytes,
                filename="shift_handover_log.jpg",
                user_id="engineer_42",
                title_override="Shift Log Aug 12",
            )

            assert res["success"] is True
            assert res["status"] == "NEEDS_REVIEW"
            note = res["note"]
            assert note["id"] is not None
            assert note["ocr_status"] == "COMPLETED"
            assert note["verification_status"] == "NEEDS_REVIEW"
            assert len(note["raw_ocr_text"]) > 0
            assert len(note["verified_text"]) > 0
            assert res["ocr_run"]["attempt"] == 1

            # 2. Test Idempotency (uploading same image again returns duplicate detection)
            duplicate_res = await test_service.ingest_handwritten_note(
                file_bytes=img_bytes,
                filename="shift_handover_log_copy.jpg",
                user_id="engineer_42",
            )
            assert duplicate_res["status"] == "DUPLICATE"
            assert duplicate_res["is_duplicate"] is True

            # 3. Human Verification Flow
            verified_text = (
                "DRILLING LOG -- VERIFIED BY LEAD ENGINEER\n"
                "Date: 12/08/2026 | Standpipe Pressure: 185 bar | Flow: 2400 L/min\n"
                "Action: Valve seal replaced successfully."
            )
            verified_note = await test_service.verify_note(
                note_id=note["id"],
                verified_text=verified_text,
                user_id="lead_engineer_01",
                title="Verified Shift Log Aug 12",
            )

            assert verified_note is not None
            assert verified_note["verification_status"] == "VERIFIED"
            assert verified_note["verified_by"] == "lead_engineer_01"
            assert verified_note["verified_at"] is not None
            assert verified_note["verified_text"] == verified_text
            # Critical principle: RAW OCR text MUST be preserved untouched
            assert verified_note["raw_ocr_text"] == note["raw_ocr_text"]

            # 4. Export Note
            json_content, ctype = test_service.export_note(note["id"], "json")
            assert ctype == "application/json"
            parsed_json = json.loads(json_content)
            assert parsed_json["status"] == "VERIFIED"
            assert parsed_json["provenance"]["verified_by"] == "lead_engineer_01"

            txt_content, txt_type = test_service.export_note(note["id"], "txt")
            assert "TITLE: Verified Shift Log Aug 12" in txt_content

            # 5. Metrics Calculation
            metrics = test_service.get_dashboard_metrics()
            assert metrics["total_notes"] == 1
            assert metrics["verified"] == 1
            assert metrics["verification_rate_pct"] == 100.0

        asyncio.run(_run())
