"""
Context Builder Service
========================
Assembles retrieved chunks into a well-structured context string
suitable for LLM consumption, with explicit source citations.

CRITICAL: Only verified content appears in context.
The LLM must answer strictly from this context.
"""

import logging
import os
from typing import List, Dict, Any

from ertmac.rag.models.search_result import SearchResult

logger = logging.getLogger("ertmac.rag.services.context_builder")

_CONTEXT_HEADER = """The following are verified handwritten note excerpts retrieved from the document system.
Each excerpt is identified by its source note and section.
Answer ONLY based on the information contained in these excerpts.
If the excerpts do not contain sufficient information to answer the question, say so explicitly.

=== RETRIEVED VERIFIED DOCUMENTS ===
"""

_CONTEXT_FOOTER = """
=== END OF RETRIEVED DOCUMENTS ===
"""


class ContextBuilderService:
    """Assembles retrieved chunks into LLM-ready context."""

    def __init__(self, max_context_tokens: int = None):
        self._max_context_chars = (
            (max_context_tokens or int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "4000"))) * 4
        )  # Approximate char-to-token ratio

    def build_context(
        self,
        results: List[SearchResult],
        query: str = "",
    ) -> Dict[str, Any]:
        """
        Builds a context dict containing the assembled text and source list.

        Args:
            results: Retrieved search results (already ranked).
            query: Original query (used for context header).

        Returns:
            {
                "context_text": str,           # LLM prompt context
                "sources": List[dict],         # Source citations
                "chunk_count": int,
                "truncated": bool,             # True if context was truncated
            }
        """
        if not results:
            return {
                "context_text": "",
                "sources": [],
                "chunk_count": 0,
                "truncated": False,
            }

        context_parts = [_CONTEXT_HEADER]
        sources = []
        total_chars = len(_CONTEXT_HEADER) + len(_CONTEXT_FOOTER)
        truncated = False

        for i, result in enumerate(results, 1):
            section_label = f"[{i}] Note: {result.title} | Section: {result.section}"
            provenance_label = ""
            if result.provenance:
                provenance_label = (
                    f"   [Source: note_id={result.provenance.note_id}, "
                    f"verified_at={result.provenance.verified_at or 'N/A'}]"
                )

            block = (
                f"\n{section_label}\n"
                f"{provenance_label}\n"
                f"{result.text}\n"
                f"{'─' * 60}\n"
            )

            if total_chars + len(block) > self._max_context_chars:
                truncated = True
                logger.debug(
                    f"ContextBuilder: Truncated at {i}/{len(results)} chunks "
                    f"({total_chars}/{self._max_context_chars} chars)"
                )
                break

            context_parts.append(block)
            total_chars += len(block)

            # Build source citation
            sources.append({
                "citation_index": i,
                "note_id": result.note_id,
                "chunk_id": result.chunk_id,
                "title": result.title,
                "section": result.section,
                "relevance_score": round(result.score, 4),
                "verified_at": result.provenance.verified_at if result.provenance else None,
                "verified_by": result.provenance.verified_by if result.provenance else None,
                "source_file_id": result.provenance.source_file_id if result.provenance else None,
                "ocr_run_id": result.provenance.ocr_run_id if result.provenance else None,
                "text_preview": result.text[:200] + "..." if len(result.text) > 200 else result.text,
            })

        context_parts.append(_CONTEXT_FOOTER)
        context_text = "".join(context_parts)

        return {
            "context_text": context_text,
            "sources": sources,
            "chunk_count": len(sources),
            "truncated": truncated,
        }


# Module singleton
global_context_builder_service = ContextBuilderService()
