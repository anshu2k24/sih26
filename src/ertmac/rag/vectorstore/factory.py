"""
Vector Store Factory
=====================
Returns the configured vector store singleton based on RAG_VECTOR_STORE env var.

    pgvector  — PostgreSQL + pgvector extension (PRODUCTION)
    local     — numpy in-memory fallback (DEVELOPMENT ONLY)
"""

import logging
import os
from typing import Optional

from ertmac.rag.vectorstore.base import VectorStore

logger = logging.getLogger("ertmac.rag.vectorstore.factory")

_store_instance: Optional[VectorStore] = None


def get_vector_store(
    force_store: Optional[str] = None,
    embedding_dim: int = 384,
    initialize: bool = True,
) -> VectorStore:
    """
    Returns singleton vector store based on RAG_VECTOR_STORE env var.

    Args:
        force_store: Override env var — used in tests.
        embedding_dim: Dimension of embedding vectors.
        initialize: Whether to call store.initialize() on first creation.
    """
    global _store_instance

    if _store_instance is not None and force_store is None:
        return _store_instance

    store_type = (force_store or os.getenv("RAG_VECTOR_STORE", "local")).lower().strip()

    if store_type == "pgvector":
        from ertmac.rag.vectorstore.pgvector_store import PgVectorStore
        instance = PgVectorStore(embedding_dim=embedding_dim)
    elif store_type == "local":
        from ertmac.rag.vectorstore.local_store import LocalVectorStore
        instance = LocalVectorStore()
    else:
        logger.warning(
            f"Unknown RAG_VECTOR_STORE='{store_type}'. "
            f"Falling back to local development store."
        )
        from ertmac.rag.vectorstore.local_store import LocalVectorStore
        instance = LocalVectorStore()

    if initialize:
        try:
            instance.initialize()
        except Exception as e:
            logger.error(f"Vector store initialization failed: {e}")
            if store_type == "pgvector":
                logger.warning("pgvector init failed — falling back to local store for this session")
                from ertmac.rag.vectorstore.local_store import LocalVectorStore
                instance = LocalVectorStore()
                instance.initialize()

    logger.info(f"Vector store initialized: {instance.store_name}")

    if force_store is None:
        _store_instance = instance

    return instance


def reset_vector_store():
    """Resets the singleton — used in tests."""
    global _store_instance
    _store_instance = None
