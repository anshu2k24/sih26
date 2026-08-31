"""
Search Query Models
Structured request models for all RAG search and Q&A operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List


class SearchMode(str, Enum):
    HYBRID   = "hybrid"    # Semantic + keyword + metadata (default)
    SEMANTIC = "semantic"  # Vector similarity only
    KEYWORD  = "keyword"   # Exact/full-text only
    METADATA = "metadata"  # Metadata filtering only


@dataclass
class SearchFilters:
    """
    Optional structured filters applied during hybrid search.
    All fields are optional — missing fields are simply not applied.
    """
    # Date filters
    date_from: Optional[str] = None         # ISO date string "2026-08-01"
    date_to: Optional[str] = None           # ISO date string "2026-08-31"

    # Tag/category filters
    tags: Optional[List[str]] = None        # ["Maintenance", "Vibration"]
    document_type: Optional[str] = None     # Free-form document type label

    # Status filter (defaults to VERIFIED only — never bypass)
    verification_status: str = "VERIFIED"   # RAG always defaults to VERIFIED

    # Numeric measurement filters (generic, applied to structured_data)
    # Example: {"pressure_min": 100, "pressure_max": 500}
    numeric_filters: Optional[Dict[str, float]] = None

    # Identifier filters (exact match preferred)
    identifiers: Optional[List[str]] = None  # ["MUD-PUMP-008", "WELL-15/9-F-14"]

    # Access control context (for future multi-tenant filtering)
    organization_id: Optional[str] = None
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "tags": self.tags,
            "document_type": self.document_type,
            "verification_status": self.verification_status,
            "numeric_filters": self.numeric_filters,
            "identifiers": self.identifiers,
            "organization_id": self.organization_id,
        }


@dataclass
class SearchQuery:
    """
    Complete search request including query text and filters.
    """
    query: str
    top_k: int = 10
    mode: SearchMode = SearchMode.HYBRID
    filters: SearchFilters = field(default_factory=SearchFilters)

    # Hybrid weighting (configurable per-request, with env defaults)
    semantic_weight: float = 0.6
    keyword_weight: float = 0.4

    # Q&A mode
    generate_answer: bool = False          # Requires RAG_LLM_ENABLED=true
    max_context_tokens: int = 4000
