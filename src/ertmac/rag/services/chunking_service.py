"""
Structure-Aware Chunking Service
==================================
Splits verified notes into searchable chunks using document structure first,
falling back to paragraph and sentence boundaries before using character limits.

Chunking Priority:
    1. Section boundary (title, summary, observations, measurements, tasks, entities)
    2. Paragraph boundary (blank line separation)
    3. Sentence boundary (period/newline)
    4. Character limit (only when all above are insufficient)

Configuration:
    RAG_CHUNK_SIZE=512        (target token count per chunk)
    RAG_CHUNK_OVERLAP=64      (overlap between adjacent chunks)
    RAG_MIN_CHUNK_SIZE=50     (minimum meaningful chunk size in chars)
    RAG_MAX_CHUNK_SIZE=1024   (hard maximum in chars)
"""

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from ertmac.rag.models.rag_chunk import RAGChunk
from ertmac.rag.adapters.notes_adapter import VerifiedNoteDTO

logger = logging.getLogger("ertmac.rag.services.chunking")

# Section names from the existing StructuredExtractor output
_STRUCTURED_SECTIONS = [
    "title",
    "summary",
    "observations",
    "measurements",
    "tasks",
    "entities",
    "tags",
    "dates",
]


class ChunkingService:
    """
    Structure-aware document chunker.

    Primary strategy: use structured_data fields from the existing StructuredExtractor
    to produce semantically meaningful chunks before falling back to text splitting.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
        max_chunk_size: Optional[int] = None,
    ):
        self.chunk_size     = chunk_size     or int(os.getenv("RAG_CHUNK_SIZE", "512"))
        self.chunk_overlap  = chunk_overlap  or int(os.getenv("RAG_CHUNK_OVERLAP", "64"))
        self.min_chunk_size = min_chunk_size or int(os.getenv("RAG_MIN_CHUNK_SIZE", "50"))
        self.max_chunk_size = max_chunk_size or int(os.getenv("RAG_MAX_CHUNK_SIZE", "1024"))

    def chunk_note(
        self,
        note: VerifiedNoteDTO,
        rag_document_id: str,
    ) -> List[RAGChunk]:
        """
        Converts a verified note into a list of searchable RAGChunks.

        Args:
            note: The verified note DTO.
            rag_document_id: The id of the parent rag_documents record.

        Returns:
            Ordered list of RAGChunks ready for embedding.
        """
        chunks: List[RAGChunk] = []
        chunk_index = 0
        now = datetime.now(timezone.utc).isoformat()

        base_metadata = self._build_base_metadata(note)

        # ── Strategy 1: Section-aware chunks from structured_data ──────────
        structured = note.structured_data or {}
        section_chunks = self._extract_structured_sections(structured, base_metadata)

        for section_name, section_text in section_chunks:
            if not section_text or len(section_text.strip()) < self.min_chunk_size:
                continue

            # Split large sections into sub-chunks
            sub_chunks = self._split_text(section_text)
            for sub_text in sub_chunks:
                if len(sub_text.strip()) < self.min_chunk_size:
                    continue
                chunk = RAGChunk(
                    id=str(uuid.uuid4()),
                    rag_document_id=rag_document_id,
                    note_id=note.note_id,
                    chunk_index=chunk_index,
                    section=section_name,
                    content=sub_text.strip(),
                    metadata={**base_metadata, "section": section_name},
                    created_at=now,
                )
                chunks.append(chunk)
                chunk_index += 1

        # ── Strategy 2: Full verified_text chunking (always include) ────────
        # Provides a comprehensive searchable view of the entire document
        verified_chunks = self._chunk_full_text(
            text=note.verified_text,
            base_metadata=base_metadata,
            rag_document_id=rag_document_id,
            note_id=note.note_id,
            start_index=chunk_index,
            now=now,
        )
        chunks.extend(verified_chunks)

        # ── Fallback: Single chunk for very short documents ─────────────────
        if not chunks:
            text = note.verified_text.strip()
            if text:
                chunks.append(RAGChunk(
                    id=str(uuid.uuid4()),
                    rag_document_id=rag_document_id,
                    note_id=note.note_id,
                    chunk_index=0,
                    section="body",
                    content=text[:self.max_chunk_size],
                    metadata={**base_metadata, "section": "body"},
                    created_at=now,
                ))

        logger.debug(f"Chunked note {note.note_id} into {len(chunks)} chunks")
        return chunks

    # ── Private Helpers ───────────────────────────────────────────────────

    def _extract_structured_sections(
        self, structured: Dict[str, Any], base_metadata: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """
        Converts structured_data fields into labeled (section_name, text) pairs.
        """
        sections = []

        # Title
        title = structured.get("title", "")
        if title:
            sections.append(("title", title))

        # Summary
        summary = structured.get("summary", "")
        if summary:
            sections.append(("summary", summary))

        # Observations — each becomes its own searchable chunk
        observations = structured.get("observations", [])
        if observations:
            obs_text = "\n".join(f"- {o}" for o in observations if o)
            sections.append(("observations", obs_text))

        # Tasks / Action items
        tasks = structured.get("tasks", [])
        if tasks:
            task_text = "\n".join(f"- {t}" for t in tasks if t)
            sections.append(("tasks", task_text))

        # Measurements — serialized as key=value strings for searchability
        measurements = structured.get("measurements", [])
        if measurements:
            meas_lines = []
            for m in measurements:
                if isinstance(m, dict):
                    param = m.get("parameter", "")
                    value = m.get("value", "")
                    if param and value:
                        meas_lines.append(f"{param}: {value}")
            if meas_lines:
                sections.append(("measurements", "\n".join(meas_lines)))

        # Entities (identifiers + people) — critical for exact identifier search
        entities = structured.get("entities", [])
        if entities:
            entity_lines = []
            for e in entities:
                if isinstance(e, dict):
                    kind = e.get("type", e.get("role", ""))
                    value = e.get("value", e.get("name", ""))
                    if value:
                        entity_lines.append(f"{kind}: {value}" if kind else value)
            if entity_lines:
                sections.append(("entities", "\n".join(entity_lines)))

        return sections

    def _chunk_full_text(
        self,
        text: str,
        base_metadata: Dict[str, Any],
        rag_document_id: str,
        note_id: str,
        start_index: int,
        now: str,
    ) -> List[RAGChunk]:
        """Splits the full verified_text into overlapping chunks."""
        if not text or not text.strip():
            return []

        text_chunks = self._split_text(text)
        result = []
        for i, chunk_text in enumerate(text_chunks):
            if len(chunk_text.strip()) < self.min_chunk_size:
                continue
            result.append(RAGChunk(
                id=str(uuid.uuid4()),
                rag_document_id=rag_document_id,
                note_id=note_id,
                chunk_index=start_index + i,
                section="body",
                content=chunk_text.strip(),
                metadata={**base_metadata, "section": "body"},
                created_at=now,
            ))
        return result

    def _split_text(self, text: str) -> List[str]:
        """
        Splits text into chunks preferring paragraph → sentence → character boundaries.
        Returns overlapping chunks based on chunk_size and chunk_overlap settings.
        """
        text = text.strip()
        if not text:
            return []

        # If short enough, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]

        # Try paragraph-based splitting first
        paragraphs = re.split(r"\n\s*\n", text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if len(paragraphs) > 1:
            return self._merge_into_chunks(paragraphs)

        # Try sentence-based splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 1:
            return self._merge_into_chunks(sentences)

        # Hard character split as last resort
        return self._hard_split(text)

    def _merge_into_chunks(self, units: List[str]) -> List[str]:
        """Merges text units (paragraphs/sentences) into chunk_size-bounded strings with overlap."""
        chunks = []
        current = []
        current_len = 0

        for unit in units:
            unit_len = len(unit)

            if current_len + unit_len > self.chunk_size and current:
                # Finalize current chunk
                chunks.append(" ".join(current))

                # Create overlap: keep last few units
                overlap_units = []
                overlap_len = 0
                for u in reversed(current):
                    if overlap_len + len(u) > self.chunk_overlap:
                        break
                    overlap_units.insert(0, u)
                    overlap_len += len(u) + 1
                current = overlap_units
                current_len = overlap_len

            current.append(unit)
            current_len += unit_len + 1

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _hard_split(self, text: str) -> List[str]:
        """Character-level split with overlap as absolute last resort."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
            if start >= len(text):
                break
        return chunks

    def _build_base_metadata(self, note: VerifiedNoteDTO) -> Dict[str, Any]:
        """Constructs the metadata dict preserved in every chunk."""
        structured = note.structured_data or {}
        return {
            "note_id": note.note_id,
            "title": note.title,
            "verification_status": note.verification_status,
            "verified_by": note.verified_by,
            "verified_at": note.verified_at,
            "source_file_id": note.source_file_id,
            "ocr_run_id": note.ocr_run_id,
            "organization_id": note.organization_id,
            # Structured data for filtering
            "date": structured.get("date"),
            "all_dates": structured.get("all_dates", []),
            "tags": structured.get("tags", []),
            "entity_values": [
                e.get("value", e.get("name", ""))
                for e in (structured.get("entities") or [])
                if isinstance(e, dict)
            ],
            "has_measurements": bool(structured.get("measurements")),
            "has_observations": bool(structured.get("observations")),
        }


# Module singleton
global_chunking_service = ChunkingService()
