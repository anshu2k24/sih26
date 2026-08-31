"""
Search Result Model
Normalized retrieval result returned by all search operations.

Every result carries full provenance so the user can trace:
    RAG Answer → Retrieved Chunk → Verified Note → OCR Run → Original Image
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ProvenanceInfo:
    """Full traceability chain from chunk back to original handwritten image."""
    note_id: str
    chunk_id: Optional[str] = None
    source_file_id: Optional[str] = None
    ocr_run_id: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    version: int = 1
    verification_status: str = "VERIFIED"

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "chunk_id": self.chunk_id,
            "source_file_id": self.source_file_id,
            "ocr_run_id": self.ocr_run_id,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
            "version": self.version,
            "verification_status": self.verification_status,
        }


@dataclass
class SearchResult:
    """
    A single result from any search strategy (semantic / keyword / hybrid).

    score: normalized [0.0, 1.0] — higher is more relevant
    """
    note_id: str
    chunk_id: str
    title: str
    section: str
    text: str                                        # The relevant passage
    score: float                                     # Relevance score [0.0 - 1.0]
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Optional[ProvenanceInfo] = None

    # Search signal breakdown (for transparency)
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    metadata_score: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "section": self.section,
            "text": self.text,
            "score": round(self.score, 4),
            "metadata": self.metadata,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "score_breakdown": {
                "semantic": round(self.semantic_score, 4) if self.semantic_score is not None else None,
                "keyword": round(self.keyword_score, 4) if self.keyword_score is not None else None,
                "metadata": round(self.metadata_score, 4) if self.metadata_score is not None else None,
            },
        }
