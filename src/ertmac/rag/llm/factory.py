"""
LLM Provider Factory
=====================
Returns the configured LLM provider based on RAG_LLM_PROVIDER env var.
"""

import logging
import os
from typing import Optional

from ertmac.rag.llm.base import LLMProvider

logger = logging.getLogger("ertmac.rag.llm.factory")

_llm_instance: Optional[LLMProvider] = None


def get_llm_provider(force_provider: Optional[str] = None) -> LLMProvider:
    """
    Returns singleton LLM provider.

    Supported values for RAG_LLM_PROVIDER:
        mistral  — Mistral AI chat completions (default)
    """
    global _llm_instance

    if _llm_instance is not None and force_provider is None:
        return _llm_instance

    provider_name = (
        force_provider or os.getenv("RAG_LLM_PROVIDER", "mistral")
    ).lower().strip()

    if provider_name == "mistral":
        from ertmac.rag.llm.mistral_llm import MistralLLMProvider
        instance = MistralLLMProvider()
    else:
        logger.warning(
            f"Unknown RAG_LLM_PROVIDER='{provider_name}'. Defaulting to mistral."
        )
        from ertmac.rag.llm.mistral_llm import MistralLLMProvider
        instance = MistralLLMProvider()

    logger.info(f"LLM provider initialized: {instance.provider_name}")

    if force_provider is None:
        _llm_instance = instance

    return instance


def reset_llm_provider():
    """Resets the singleton — used in tests."""
    global _llm_instance
    _llm_instance = None
