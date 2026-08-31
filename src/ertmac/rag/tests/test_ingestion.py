"""
Tests: RAG Ingestion Service
=============================
Verifies the complete ingestion pipeline with mocked components.
"""

import hashlib
import pytest
from unittest.mock import MagicMock, patch

from ertmac.rag.services.ingestion_service import IngestionService
from ertmac.rag.adapters.notes_adapter import VerifiedNoteDTO, NotesAdapter
from ertmac.rag.services.chunking_service import ChunkingService
from ertmac.rag.services.embedding_service import EmbeddingService
from ertmac.rag.repositories.document_index_repository import DocumentIndexRepository
from ertmac.rag.models.rag_chunk import RAGChunk


# ── Fixtures ──────────────────────────────────────────────────────────────

def make_verified_dto(note_id="note-001", verified_text="High vibration detected near pump."):
    return VerifiedNoteDTO(
        note_id=note_id,
        title="Test Drilling Report",
        verified_text=verified_text,
        structured_data={"observations": ["High vibration detected near pump"]},
        verification_status="VERIFIED",
        verified_by="engineer-001",
        verified_at="2026-08-31T10:00:00Z",
        source_file_id="file-001",
        ocr_run_id="run-001",
    )


def make_mock_notes_adapter(dto: VerifiedNoteDTO = None, note_info: dict = None):
    adapter = MagicMock(spec=NotesAdapter)
    adapter.get_verified_note.return_value = dto
    adapter.get_note_for_ingestion_check.return_value = note_info or (
        {
            "note_id": dto.note_id if dto else "note-001",
            "verification_status": "VERIFIED",
            "has_verified_text": True,
            "title": "Test Report",
            "updated_at": "2026-08-31T10:00:00Z",
        }
        if dto
        else None
    )
    return adapter


def make_mock_chunker(chunks=None):
    chunker = MagicMock(spec=ChunkingService)
    if chunks is None:
        chunks = [
            RAGChunk(
                id="chunk-001",
                rag_document_id="doc-001",
                note_id="note-001",
                chunk_index=0,
                section="observations",
                content="High vibration detected near pump.",
                metadata={"title": "Test Report"},
                embedding=None,
            )
        ]
    chunker.chunk_note.return_value = chunks
    return chunker


def make_mock_embedder(dim=384):
    embedder = MagicMock(spec=EmbeddingService)
    embedder.dimension = dim

    def embed_chunks(chunks):
        for c in chunks:
            c.embedding = [0.1] * dim
        return chunks

    embedder.embed_chunks.side_effect = embed_chunks
    return embedder


def make_mock_store():
    store = MagicMock()
    store.delete_by_note_id.return_value = 0
    store.upsert_chunks.return_value = None
    store.upsert_rag_document.return_value = None
    return store


# ── Tests ─────────────────────────────────────────────────────────────────

class TestIngestionService:

    def _make_service(self, notes_dto=None, note_info=None):
        """Builds an IngestionService with all mocked dependencies."""
        dto = notes_dto if notes_dto is not None else make_verified_dto()
        adapter = make_mock_notes_adapter(dto=dto, note_info=note_info)
        chunker = make_mock_chunker()
        embedder = make_mock_embedder()
        doc_repo = DocumentIndexRepository()
        store = make_mock_store()

        service = IngestionService(
            notes_adapter=adapter,
            chunking_service=chunker,
            embedding_service=embedder,
            doc_index_repo=doc_repo,
        )
        # Patch vector store factory
        service._store = store
        return service, store

    def test_verified_note_indexes_successfully(self):
        """A VERIFIED note with content should index successfully."""
        service, store = self._make_service()

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=store):
            result = service.index_note(note_id="note-001", user_id="user-001")

        assert result["success"] is True
        assert result["status"] == "INDEXED"
        assert result["chunk_count"] >= 1
        store.upsert_chunks.assert_called_once()

    def test_unverified_note_is_rejected(self):
        """Notes with verification_status != VERIFIED must be rejected."""
        adapter = MagicMock(spec=NotesAdapter)
        adapter.get_verified_note.return_value = None
        adapter.get_note_for_ingestion_check.return_value = {
            "note_id": "note-002",
            "verification_status": "NEEDS_REVIEW",
            "has_verified_text": True,
            "title": "Draft Note",
            "updated_at": "2026-08-31T10:00:00Z",
        }

        service = IngestionService(
            notes_adapter=adapter,
            chunking_service=make_mock_chunker(),
            embedding_service=make_mock_embedder(),
            doc_index_repo=DocumentIndexRepository(),
        )

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=make_mock_store()):
            result = service.index_note(note_id="note-002", user_id="user-001")

        assert result["success"] is False
        assert result["status"] == "REJECTED"
        assert "VERIFIED" in result["error"]

    def test_nonexistent_note_is_rejected(self):
        """Non-existent notes return a clear not-found error."""
        adapter = MagicMock(spec=NotesAdapter)
        adapter.get_verified_note.return_value = None
        adapter.get_note_for_ingestion_check.return_value = None

        service = IngestionService(
            notes_adapter=adapter,
            chunking_service=make_mock_chunker(),
            embedding_service=make_mock_embedder(),
            doc_index_repo=DocumentIndexRepository(),
        )

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=make_mock_store()):
            result = service.index_note(note_id="nonexistent-note", user_id="user-001")

        assert result["success"] is False
        assert result["status"] == "REJECTED"

    def test_empty_verified_text_is_rejected(self):
        """Notes with empty verified_text return an error."""
        adapter = MagicMock(spec=NotesAdapter)
        adapter.get_verified_note.return_value = None
        adapter.get_note_for_ingestion_check.return_value = {
            "note_id": "note-003",
            "verification_status": "VERIFIED",
            "has_verified_text": False,
            "title": "Empty Note",
            "updated_at": "2026-08-31T10:00:00Z",
        }

        service = IngestionService(
            notes_adapter=adapter,
            chunking_service=make_mock_chunker(),
            embedding_service=make_mock_embedder(),
            doc_index_repo=DocumentIndexRepository(),
        )

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=make_mock_store()):
            result = service.index_note(note_id="note-003", user_id="user-001")

        assert result["success"] is False

    def test_duplicate_same_version_is_skipped(self):
        """Re-indexing unchanged content returns ALREADY_INDEXED without re-embedding."""
        service, store = self._make_service()

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=store):
            # First index
            result1 = service.index_note(note_id="note-001", user_id="user-001")
            assert result1["success"] is True

            # Second index with same content — should be skipped (same content hash)
            result2 = service.index_note(note_id="note-001", user_id="user-001")

        assert result2["status"] == "ALREADY_INDEXED"
        assert result2.get("skipped") is True
        assert store.upsert_chunks.call_count == 1

    def test_force_reindex_replaces_existing_chunks(self):
        """force_reindex=True should delete existing chunks and reindex."""
        dto = make_verified_dto()
        adapter = make_mock_notes_adapter(dto=dto)
        chunker = make_mock_chunker()
        embedder = make_mock_embedder()
        doc_repo = DocumentIndexRepository()
        store = make_mock_store()
        store.delete_by_note_id.return_value = 3  # Simulate 3 existing chunks

        service = IngestionService(
            notes_adapter=adapter,
            chunking_service=chunker,
            embedding_service=embedder,
            doc_index_repo=doc_repo,
        )

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=store):
            result1 = service.index_note(note_id="note-001", user_id="user-001")
            assert result1["success"] is True

            result2 = service.index_note(
                note_id="note-001", user_id="user-001", force_reindex=True
            )

        assert result2["success"] is True
        assert result2["status"] == "INDEXED"
        assert store.delete_by_note_id.called

    def test_version_increments_on_reindex(self):
        """Version number should increment each time content is reindexed."""
        dto = make_verified_dto(note_id="note-ver-1", verified_text="Version 1 content.")
        dto2 = make_verified_dto(note_id="note-ver-1", verified_text="Version 2 updated content.")

        adapter = MagicMock(spec=NotesAdapter)
        adapter.get_verified_note.side_effect = [dto, dto2]
        adapter.get_note_for_ingestion_check.return_value = {
            "note_id": "note-ver-1",
            "verification_status": "VERIFIED",
            "has_verified_text": True,
            "title": "Report",
            "updated_at": "2026-08-31T10:00:00Z",
        }

        chunker = make_mock_chunker()
        embedder = make_mock_embedder()
        doc_repo = DocumentIndexRepository()
        store = make_mock_store()

        service = IngestionService(
            notes_adapter=adapter,
            chunking_service=chunker,
            embedding_service=embedder,
            doc_index_repo=doc_repo,
        )

        with patch("ertmac.rag.services.ingestion_service.get_vector_store", return_value=store):
            r1 = service.index_note(note_id="note-ver-1", user_id="user-001")
            r2 = service.index_note(note_id="note-ver-1", user_id="user-001", force_reindex=True)

        assert r1["version"] == 1
        assert r2["version"] == 2
