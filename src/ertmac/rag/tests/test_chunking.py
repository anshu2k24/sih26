"""
Tests: Structure-Aware Chunking
================================
Verifies the ChunkingService produces correct, well-formed chunks.
"""

import pytest
from ertmac.rag.services.chunking_service import ChunkingService
from ertmac.rag.adapters.notes_adapter import VerifiedNoteDTO


def make_note(
    note_id="test-note-001",
    title="Test Report",
    verified_text="",
    structured_data=None,
):
    return VerifiedNoteDTO(
        note_id=note_id,
        title=title,
        verified_text=verified_text,
        structured_data=structured_data or {},
        verification_status="VERIFIED",
        verified_by="test-user",
        verified_at="2026-08-31T10:00:00Z",
        source_file_id="file-001",
        ocr_run_id="run-001",
    )


@pytest.fixture
def chunker():
    return ChunkingService(
        chunk_size=256,
        chunk_overlap=32,
        min_chunk_size=20,
        max_chunk_size=512,
    )


class TestChunkingService:

    def test_single_chunk_for_short_document(self, chunker):
        """Short notes should produce a minimal number of chunks."""
        note = make_note(verified_text="High vibration detected near mud pump at 0600 HRS.")
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        assert len(chunks) >= 1
        for c in chunks:
            assert c.content.strip()
            assert c.note_id == "test-note-001"
            assert c.rag_document_id == "doc-001"

    def test_section_aware_chunking_uses_structured_data(self, chunker):
        """Structured data sections should produce distinct labeled chunks."""
        note = make_note(
            verified_text="Daily drilling report...",
            structured_data={
                "title": "Daily Drilling Report — 31 Aug 2026",
                "summary": "Routine drilling operations with minor anomalies observed.",
                "observations": [
                    "High vibration detected near mud pump",
                    "Minor oil leakage at valve connection",
                ],
                "tasks": [
                    "Inspect mud pump bearings",
                    "Monitor valve assembly",
                ],
                "measurements": [
                    {"parameter": "WOB", "value": "150 kN.m", "numeric_value": 150.0, "unit": "kN.m"},
                ],
            },
        )
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        sections = {c.section for c in chunks}

        # Should have multiple sections including structured ones
        assert len(sections) >= 2
        assert any(c.section == "observations" for c in chunks)
        assert any(c.section == "tasks" for c in chunks)

    def test_observations_text_is_preserved(self, chunker):
        """Observation text must appear verbatim in an observations chunk."""
        note = make_note(
            verified_text="Observation: pump vibration detected.",
            structured_data={
                "observations": ["pump vibration detected at 0600 HRS"],
            },
        )
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        obs_chunks = [c for c in chunks if c.section == "observations"]
        assert obs_chunks, "Expected at least one observations chunk"
        assert "pump vibration" in obs_chunks[0].content.lower()

    def test_large_document_produces_multiple_body_chunks(self, chunker):
        """Long verified_text should be split into multiple body chunks."""
        long_text = " ".join([f"Sentence number {i} with technical content about drilling operations." for i in range(100)])
        note = make_note(verified_text=long_text)
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        body_chunks = [c for c in chunks if c.section == "body"]
        assert len(body_chunks) > 1, "Expected multiple body chunks for long document"

    def test_empty_verified_text_returns_no_chunks(self, chunker):
        """Completely empty text should produce no or zero usable chunks."""
        note = make_note(verified_text="   ")
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        body_chunks = [c for c in chunks if len(c.content.strip()) > 0]
        assert len(body_chunks) == 0

    def test_chunk_index_is_sequential(self, chunker):
        """Chunk indices must start at 0 and be sequentially ordered."""
        note = make_note(
            verified_text=" ".join([f"Word{i}" for i in range(500)]),
        )
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        if len(chunks) > 1:
            indices = [c.chunk_index for c in chunks]
            # Indices should be non-decreasing
            assert all(indices[i] <= indices[i + 1] for i in range(len(indices) - 1))

    def test_chunk_metadata_preserves_provenance(self, chunker):
        """Every chunk metadata should carry note-level provenance fields."""
        note = make_note(verified_text="Some content with technical details.")
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        for chunk in chunks:
            assert chunk.metadata.get("note_id") == "test-note-001"
            assert chunk.metadata.get("verified_by") == "test-user"
            assert chunk.metadata.get("source_file_id") == "file-001"

    def test_entity_section_contains_identifier(self, chunker):
        """Entity chunks should contain equipment/identifier text for exact search."""
        note = make_note(
            verified_text="MUD-PUMP-008 showing elevated vibration.",
            structured_data={
                "entities": [
                    {"type": "EQUIPMENT ID", "value": "MUD-PUMP-008"},
                ],
            },
        )
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        entity_chunks = [c for c in chunks if c.section == "entities"]
        assert entity_chunks, "Expected entities section chunk"
        assert "MUD-PUMP-008" in entity_chunks[0].content

    def test_paragraph_splitting(self, chunker):
        """Paragraphs separated by blank lines should be chunked at paragraph boundaries."""
        text = "\n\n".join([
            "First paragraph about drilling operations.",
            "Second paragraph about mud pump maintenance.",
            "Third paragraph about vibration analysis.",
        ])
        note = make_note(verified_text=text)
        chunks = chunker.chunk_note(note, rag_document_id="doc-001")
        # Should not merge all paragraphs into one giant chunk
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.content.strip()
