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
        gemini   — Google Gemini API (gemini-1.5-flash, gemini-2.0-flash)
        mistral  — Mistral AI chat completions
    """
    global _llm_instance

    if _llm_instance is not None and force_provider is None:
        return _llm_instance

    default_prov = "gemini" if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") else os.getenv("RAG_LLM_PROVIDER", "gemini")
    provider_name = (
        force_provider or os.getenv("RAG_LLM_PROVIDER", default_prov)
    ).lower().strip()

    if provider_name in ("gemini", "google"):
        from ertmac.rag.llm.gemini_llm import GeminiLLMProvider
        instance = GeminiLLMProvider()
    elif provider_name == "mistral":
        from ertmac.rag.llm.mistral_llm import MistralLLMProvider
        instance = MistralLLMProvider()
    else:
        logger.info(f"Using Gemini LLM provider for '{provider_name}'")
        from ertmac.rag.llm.gemini_llm import GeminiLLMProvider
        instance = GeminiLLMProvider()

    logger.info(f"LLM provider initialized: {instance.provider_name}")

    if force_provider is None:
        _llm_instance = instance

    return instance


def reset_llm_provider():
    """Resets the singleton — used in tests."""
    global _llm_instance
    _llm_instance = None
