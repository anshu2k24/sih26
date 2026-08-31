"""
Mistral LLM Provider for RAG Answer Generation
================================================
Uses Mistral AI chat completions to generate context-grounded answers.

Configuration:
    RAG_LLM_PROVIDER=mistral
    RAG_LLM_MODEL=mistral-small-latest
    MISTRAL_API_KEY=your-api-key
    pip install mistralai

Note: Already used by existing OCR pipeline (Mistral Vision).
"""

import logging
import os

from ertmac.rag.llm.base import LLMProvider

logger = logging.getLogger("ertmac.rag.llm.mistral")


class MistralLLMProvider(LLMProvider):
    """Mistral AI chat completion provider for RAG Q&A."""

    def __init__(self, api_key: str = None, default_model: str = None):
        self._api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        self._default_model = default_model or os.getenv("RAG_LLM_MODEL", "mistral-small-latest")
        self._client = None

    @property
    def provider_name(self) -> str:
        return f"mistral/{self._default_model}"

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "MISTRAL_API_KEY is not set. Cannot use Mistral LLM. "
                    "Set RAG_LLM_ENABLED=false to disable answer generation."
                )
            try:
                from mistralai import Mistral
                self._client = Mistral(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "mistralai package not installed. Run: pip install mistralai"
                )
        return self._client

    def generate_answer(
        self,
        question: str,
        context: str,
        system_prompt: str = "",
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        """Generates a grounded answer using Mistral chat completion."""
        client = self._get_client()
        use_model = model or self._default_model

        messages = [
            {"role": "system", "content": system_prompt or "You are a helpful assistant."},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {question}\n\n"
                    "Answer based strictly on the context above:"
                ),
            },
        ]

        try:
            response = client.chat.complete(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Mistral LLM generation failed: {e}") from e

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            # Minimal probe
            client.chat.complete(
                model=self._default_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning(f"Mistral LLM health check failed: {e}")
            return False
