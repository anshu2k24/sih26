"""
RAG Chunk Model
A single searchable unit within a RAG-indexed document.

Each chunk preserves:
- Its text content
- Its section within the source document
- Its embedding vector
- Its full provenance back to the verified note
- Its metadata for structured filtering
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class RAGChunk:
    """
    A single searchable passage from a verified note.

    Provenance chain:
        RAGChunk.chunk_id
            → RAGChunk.rag_document_id → rag_documents.id
            → RAGChunk.note_id → handwritten_notes.id
    """
    note_id: str
    chunk_index: int               # 0-based ordering within the document
    section: str                   # Section label: "title" | "summary" | "observations" | etc.
    content: str                   # The actual searchable text for this chunk
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Set after storage
    id: Optional[str] = None
    rag_document_id: Optional[str] = None

    # Embedding vector — not exposed in API responses
    embedding: Optional[List[float]] = None

    # Timestamps
    created_at: Optional[str] = None

    def to_dict(self, include_embedding: bool = False) -> dict:
        d = {
            "id": self.id,
            "rag_document_id": self.rag_document_id,
            "note_id": self.note_id,
            "chunk_index": self.chunk_index,
            "section": self.section,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
        if include_embedding and self.embedding is not None:
            d["embedding"] = self.embedding
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RAGChunk":
        return cls(
            id=data.get("id"),
            rag_document_id=data.get("rag_document_id"),
            note_id=data["note_id"],
            chunk_index=data.get("chunk_index", 0),
            section=data.get("section", "body"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            created_at=data.get("created_at"),
        )
