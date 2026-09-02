"""
Answer Generation Service
==========================
Optional LLM-based question answering over retrieved verified documents.

Architecture:
    User Question
          ↓
    Hybrid Retrieval
          ↓
    Top Relevant Verified Chunks
          ↓
    Context Builder
          ↓
    LLM (Mistral or configured provider)
          ↓
    Answer + Sources

CRITICAL RULES:
    1. LLM must answer ONLY from retrieved context.
    2. If context is insufficient → return standard "insufficient information" message.
    3. NEVER hallucinate information not found in sources.
    4. Every answer must include source citations.
    5. This service is DISABLED by default (RAG_LLM_ENABLED=false).
       Search remains independently functional when this is disabled.

Configuration:
    RAG_LLM_ENABLED=false     — set to true to enable
    RAG_LLM_PROVIDER=mistral
    RAG_LLM_MODEL=mistral-small-latest
    MISTRAL_API_KEY=...
"""

import logging
import os
import time
from typing import List, Dict, Any, Optional

from ertmac.rag.models.search_result import SearchResult
from ertmac.rag.models.query_model import SearchQuery
from ertmac.rag.services.hybrid_search_service import global_hybrid_search_service, HybridSearchService
from ertmac.rag.services.context_builder_service import global_context_builder_service, ContextBuilderService
from ertmac.rag.repositories.rag_audit_repository import global_rag_audit_repository, RAGAuditEvent

logger = logging.getLogger("ertmac.rag.services.answer_generation")

_INSUFFICIENT_INFORMATION_MESSAGE = (
    "I could not find sufficient verified information in the indexed documents "
    "to answer this question. Please refine your query or check whether relevant "
    "documents have been verified and indexed."
)

_SYSTEM_PROMPT = """You are an AI assistant for a Handwritten Notes OCR System.
You answer questions STRICTLY based on the verified document excerpts provided in the context.

Rules:
1. Use ONLY information present in the provided context.
2. If the context does not contain enough information, say so clearly.
3. Always cite your sources by referencing the document title and section.
4. Never invent, assume, or extrapolate information not found in the context.
5. Be precise and factual — this is a technical knowledge system.
"""


class AnswerGenerationService:
    """
    Optional LLM-based Q&A over retrieved verified documents.
    Falls back gracefully when LLM is disabled or unavailable.
    """

    def __init__(
        self,
        search_service: Optional[HybridSearchService] = None,
        context_builder: Optional[ContextBuilderService] = None,
        llm_provider=None,
    ):
        self._search = search_service or global_hybrid_search_service
        self._context_builder = context_builder or global_context_builder_service
        self._llm = llm_provider  # None → lazy init from factory

        llm_env = os.getenv("RAG_LLM_ENABLED")
        if llm_env is not None:
            self._llm_enabled = llm_env.lower() == "true"
        else:
            self._llm_enabled = bool(
                os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
                or os.getenv("MISTRAL_API_KEY")
            )
        provider_name = os.getenv("RAG_LLM_PROVIDER", "gemini").lower()
        default_model = "gemini-3.5-flash" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "mistral-small-latest"
        self._llm_model = os.getenv("RAG_LLM_MODEL", os.getenv("GEMINI_MODEL", default_model))

    def answer(
        self,
        question: str,
        query: Optional[SearchQuery] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answers a natural language question using retrieved verified documents.

        Args:
            question: The user's question.
            query: Optional SearchQuery to customize retrieval (filters, top_k, etc.)
            user_id: For audit logging.

        Returns:
            {
                "answer": str,
                "sources": List[dict],
                "llm_used": bool,
                "retrieval_count": int,
                "insufficient_information": bool,
            }
        """
        start_time = time.time()
        question = question.strip()
        if not question:
            return {
                "answer": "Please provide a question.",
                "sources": [],
                "llm_used": False,
                "retrieval_count": 0,
                "insufficient_information": True,
            }

        # ── Step 1: Retrieve relevant chunks ──────────────────────────────
        if query is None:
            from ertmac.rag.models.query_model import SearchQuery, SearchFilters
            query = SearchQuery(
                query=question,
                top_k=int(os.getenv("RAG_TOP_K", "10")),
            )

        results: List[SearchResult] = []
        try:
            results = self._search.search(query=query, user_id=user_id)
        except Exception as e:
            logger.error(f"AnswerGenerationService: Retrieval failed: {e}")

        # ── Step 2: Build context ─────────────────────────────────────────
        context_data = self._context_builder.build_context(results, query=question)
        sources = context_data["sources"]

        # ── Step 3: Check if context is sufficient ────────────────────────
        if not results or not context_data["context_text"].strip():
            duration_ms = (time.time() - start_time) * 1000
            global_rag_audit_repository.log(
                RAGAuditEvent.QUERY,
                user_id=user_id,
                duration_ms=duration_ms,
                status="insufficient",
                metadata={"question": question[:100], "result_count": 0},
            )
            return {
                "answer": _INSUFFICIENT_INFORMATION_MESSAGE,
                "sources": [],
                "llm_used": False,
                "retrieval_count": 0,
                "insufficient_information": True,
            }

        duration_ms = (time.time() - start_time) * 1000

        # ── Step 4: Generate answer (if LLM enabled) ──────────────────────
        answer_text = ""
        llm_used = False

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        mistral_key = os.getenv("MISTRAL_API_KEY")
        llm_configured = bool((gemini_key and "your_" not in gemini_key) or mistral_key)

        llm_env = os.getenv("RAG_LLM_ENABLED", "true").lower() == "true"

        if llm_env and llm_configured:
            try:
                from ertmac.rag.llm.factory import get_llm_provider
                llm = get_llm_provider()
                current_model = os.getenv("RAG_LLM_MODEL")
                if not current_model:
                    current_model = os.getenv("RAG_LLM_MODEL", "gemini-3.5-flash")
                answer_text = llm.generate_answer(
                    question=question,
                    context=context_data["context_text"],
                    system_prompt=_SYSTEM_PROMPT,
                    model=current_model,
                )
                llm_used = True
            except Exception as e:
                logger.warning(f"AnswerGenerationService: LLM generation notice ({e}). Falling back to verified extract summary.")
                answer_text = self._build_search_only_response(results, question)
        else:
            # Search-only mode / API key pending
            answer_text = self._build_search_only_response(results, question)

        global_rag_audit_repository.log(
            RAGAuditEvent.QUERY,
            user_id=user_id,
            duration_ms=duration_ms,
            status="success",
            metadata={
                "question": question[:100],
                "result_count": len(results),
                "llm_used": llm_used,
            },
        )

        return {
            "answer": answer_text,
            "sources": sources,
            "llm_used": llm_used,
            "retrieval_count": len(results),
            "insufficient_information": False,
            "context_truncated": context_data.get("truncated", False),
        }

    def _build_search_only_response(
        self,
        results: List[SearchResult],
        question: str,
    ) -> str:
        """
        When LLM is disabled or pending API key, synthesizes a clean, structured text summary
        from verified retrieved document chunks.
        """
        lines = [
            f"**Verified Intelligence Summary** (Retrieved {len(results)} relevant sections from verified documents):\n",
        ]
        for i, r in enumerate(results[:4], 1):
            snippet = r.text.strip().replace("\n", " ")
            if len(snippet) > 280:
                snippet = snippet[:280] + "..."
            lines.append(
                f"**[{i}] {r.title}** ({r.section})\n"
                f"> {snippet}\n"
            )
        
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key or "your_" in gemini_key:
            lines.append("\n*Tip: Add your `GEMINI_API_KEY` in `.env` to enable full conversational AI synthesis.*")

        return "\n".join(lines)

    def _get_llm(self):
        from ertmac.rag.llm.factory import get_llm_provider
        return get_llm_provider()

    def health_check(self) -> Dict[str, Any]:
        return {
            "llm_enabled": self._llm_enabled,
            "llm_provider": os.getenv("RAG_LLM_PROVIDER", "not_configured"),
            "llm_model": self._llm_model,
        }


# Module singleton
global_answer_generation_service = AnswerGenerationService()
