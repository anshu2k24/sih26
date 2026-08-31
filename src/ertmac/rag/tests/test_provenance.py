"""
Tests: Provenance Chain Integrity
===================================
Verifies that every retrieved result can be traced back to its source.
"""

import pytest
from unittest.mock import MagicMock, patch

from ertmac.rag.adapters.provenance_adapter import ProvenanceAdapter
from ertmac.rag.adapters.notes_adapter import NotesAdapter
from ertmac.rag.models.search_result import ProvenanceInfo


def make_mock_note(note_id="note-001"):
    return {
        "id": note_id,
        "title": "Test Drilling Report",
        "verified_text": "High vibration detected near pump.",
        "raw_ocr_text": "Hi9h vibration detectd near pomp.",
        "verification_status": "VERIFIED",
        "verified_by": "engineer-001",
        "verified_at": "2026-08-31T10:00:00Z",
        "source_file_id": "file-001",
        "latest_ocr_run_id": "run-001",
        "is_deleted": False,
        "metadata": {"organization_id": "org-001"},
        "ocr_status": "COMPLETED",
    }


class TestProvenanceAdapter:

    def test_provenance_contains_note_id(self):
        """Provenance must always contain note_id."""
        note = make_mock_note()
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = note
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(note_id="note-001", chunk_id="chunk-001")
        assert prov.note_id == "note-001"

    def test_provenance_contains_source_file_id(self):
        """Provenance should carry source_file_id for tracing to original image."""
        note = make_mock_note()
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = note
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(note_id="note-001", chunk_id="chunk-001")
        assert prov.source_file_id == "file-001"

    def test_provenance_contains_ocr_run_id(self):
        """Provenance should carry latest_ocr_run_id for OCR chain traceability."""
        note = make_mock_note()
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = note
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(note_id="note-001", chunk_id="chunk-001")
        assert prov.ocr_run_id == "run-001"

    def test_provenance_contains_verified_at(self):
        """Provenance should preserve the verification timestamp."""
        note = make_mock_note()
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = note
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(note_id="note-001", chunk_id="chunk-001")
        assert prov.verified_at == "2026-08-31T10:00:00Z"

    def test_provenance_contains_chunk_id(self):
        """Provenance must carry chunk_id for exact chunk retrieval."""
        note = make_mock_note()
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = note
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(
            note_id="note-001",
            chunk_id="chunk-xyz",
        )
        assert prov.chunk_id == "chunk-xyz"

    def test_provenance_safe_for_missing_note(self):
        """Provenance adapter must not raise even if note is deleted/missing."""
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = None
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(
            note_id="missing-note",
            chunk_id="chunk-001",
        )
        assert prov.note_id == "missing-note"
        # Should not raise — partial provenance is acceptable

    def test_provenance_verification_status_correct(self):
        """Provenance should reflect VERIFIED status for trusted content."""
        note = make_mock_note()
        mock_repo = MagicMock()
        mock_repo.get_note.return_value = note
        mock_adapter = MagicMock(spec=NotesAdapter)
        mock_adapter._repo = mock_repo
        adapter = ProvenanceAdapter(notes_adapter=mock_adapter)
        prov = adapter.build_provenance(note_id="note-001", chunk_id="chunk-001")
        assert prov.verification_status == "VERIFIED"

    def test_full_provenance_chain_is_serializable(self):
        """ProvenanceInfo.to_dict() must include all required traceability fields."""
        prov = ProvenanceInfo(
            note_id="note-001",
            chunk_id="chunk-001",
            source_file_id="file-001",
            ocr_run_id="run-001",
            verified_by="engineer-001",
            verified_at="2026-08-31T10:00:00Z",
            version=2,
            verification_status="VERIFIED",
        )
        d = prov.to_dict()
        assert d["note_id"] == "note-001"
        assert d["chunk_id"] == "chunk-001"
        assert d["source_file_id"] == "file-001"
        assert d["ocr_run_id"] == "run-001"
        assert d["verified_at"] == "2026-08-31T10:00:00Z"
        assert d["version"] == 2
        assert d["verification_status"] == "VERIFIED"
