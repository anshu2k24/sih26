"""
Local Vector Store (Development Fallback)
==========================================
Pure Python implementation using numpy cosine similarity.
Persists data to a JSON file for development continuity across restarts.

IMPORTANT:
    This store is for LOCAL DEVELOPMENT ONLY.
    It is NOT suitable for production because:
    - It stores all vectors in memory
    - Cosine search is O(n) brute force
    - No concurrent access protection

Configuration:
    RAG_VECTOR_STORE=local
    RAG_LOCAL_INDEX_PATH=data/rag_local_index.json  (optional)
"""

import json
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from ertmac.rag.vectorstore.base import VectorStore
from ertmac.rag.models.rag_chunk import RAGChunk
from ertmac.rag.models.search_result import SearchResult, ProvenanceInfo

logger = logging.getLogger("ertmac.rag.vectorstore.local")

_PRODUCTION_WARNING = (
    "⚠️  RAG_VECTOR_STORE=local — Using in-memory fallback. "
    "This is for development only. Set RAG_VECTOR_STORE=pgvector for production."
)


class LocalVectorStore(VectorStore):
    """
    Development-only vector store backed by numpy cosine similarity.
    Persists to JSON for data continuity across dev server restarts.
    """

    def __init__(self, index_path: Optional[str] = None):
        self._index_path = Path(
            index_path
            or os.getenv("RAG_LOCAL_INDEX_PATH", "data/rag_local_index.json")
        )
        self._chunks: Dict[str, Dict[str, Any]] = {}   # chunk_id -> chunk data
        self._rag_docs: Dict[str, Dict[str, Any]] = {} # note_id -> rag_document data
        logger.warning(_PRODUCTION_WARNING)

    @property
    def store_name(self) -> str:
        return "local_numpy"

    def initialize(self) -> None:
        """Loads existing index from JSON file if present."""
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._chunks = data.get("chunks", {})
                    self._rag_docs = data.get("rag_docs", {})
                logger.info(
                    f"LocalVectorStore: Loaded {len(self._chunks)} chunks from {self._index_path}"
                )
            except Exception as e:
                logger.warning(f"LocalVectorStore: Could not load index file: {e}. Starting fresh.")
                self._chunks = {}
                self._rag_docs = {}
        else:
            logger.info(f"LocalVectorStore: No existing index at {self._index_path}. Starting fresh.")

    def _save(self) -> None:
        """Persists current state to JSON."""
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump({"chunks": self._chunks, "rag_docs": self._rag_docs}, f)
        except Exception as e:
            logger.error(f"LocalVectorStore: Failed to save index: {e}")

    def upsert_chunks(self, chunks: List[RAGChunk]) -> None:
        for chunk in chunks:
            chunk_id = chunk.id or str(uuid.uuid4())
            self._chunks[chunk_id] = {
                "id": chunk_id,
                "rag_document_id": chunk.rag_document_id,
                "note_id": chunk.note_id,
                "chunk_index": chunk.chunk_index,
                "section": chunk.section,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": chunk.embedding,
                "created_at": chunk.created_at or datetime.now(timezone.utc).isoformat(),
            }
        self._save()
        logger.debug(f"LocalVectorStore: Upserted {len(chunks)} chunks")

    def upsert_rag_document(self, doc_data: Dict[str, Any]) -> None:
        self._rag_docs[doc_data["note_id"]] = doc_data
        self._save()

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Brute-force cosine similarity search."""
        filters = filters or {}
        scored = []

        for chunk_id, chunk in self._chunks.items():
            emb = chunk.get("embedding")
            if not emb:
                continue

            # Apply note_id filter if present
            if filters.get("note_id") and chunk["note_id"] != filters["note_id"]:
                continue

            score = self._cosine_similarity(query_embedding, emb)
            scored.append((score, chunk_id, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk_id, chunk in scored[:top_k]:
            results.append(SearchResult(
                note_id=chunk["note_id"],
                chunk_id=chunk_id,
                title=chunk.get("metadata", {}).get("title", "Untitled"),
                section=chunk.get("section", "body"),
                text=chunk.get("content", ""),
                score=max(0.0, min(1.0, score)),
                metadata=chunk.get("metadata", {}),
                semantic_score=score,
                provenance=ProvenanceInfo(note_id=chunk["note_id"], chunk_id=chunk_id),
            ))
        return results

    def fulltext_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Simple substring / token matching for local development."""
        query_lower = query.lower()
        query_tokens = set(query_lower.split())
        scored = []

        for chunk_id, chunk in self._chunks.items():
            content = chunk.get("content", "").lower()
            if not content:
                continue

            # Score: fraction of query tokens found in content
            content_tokens = set(content.split())
            matches = query_tokens & content_tokens
            if not matches:
                # Also check substring containment
                if query_lower not in content:
                    continue
                score = 0.3  # partial substring match
            else:
                score = len(matches) / len(query_tokens) if query_tokens else 0.0

            scored.append((score, chunk_id, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk_id, chunk in scored[:top_k]:
            results.append(SearchResult(
                note_id=chunk["note_id"],
                chunk_id=chunk_id,
                title=chunk.get("metadata", {}).get("title", "Untitled"),
                section=chunk.get("section", "body"),
                text=chunk.get("content", ""),
                score=score,
                metadata=chunk.get("metadata", {}),
                keyword_score=score,
                provenance=ProvenanceInfo(note_id=chunk["note_id"], chunk_id=chunk_id),
            ))
        return results

    def delete_by_note_id(self, note_id: str) -> int:
        """Removes all chunks for a note from the local index."""
        to_delete = [cid for cid, c in self._chunks.items() if c["note_id"] == note_id]
        for cid in to_delete:
            del self._chunks[cid]
        if note_id in self._rag_docs:
            del self._rag_docs[note_id]
        self._save()
        return len(to_delete)

    def get_chunks_for_note(self, note_id: str) -> List[RAGChunk]:
        matching = [c for c in self._chunks.values() if c["note_id"] == note_id]
        matching.sort(key=lambda c: c.get("chunk_index", 0))
        return [RAGChunk.from_dict(c) for c in matching]

    def health_check(self) -> bool:
        return True  # Local store is always available

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Computes cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
