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


import requests

class MistralLLMProvider(LLMProvider):
    """Mistral AI chat completion provider for RAG Q&A."""

    def __init__(self, api_key: str = None, default_model: str = None):
        self._api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        self._default_model = default_model or os.getenv("RAG_LLM_MODEL", "mistral-small-latest")
        self._base_url = "https://api.mistral.ai/v1"

    @property
    def provider_name(self) -> str:
        return f"mistral/{self._default_model}"

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
        if not self._api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY is not set. Cannot use Mistral LLM."
            )

        use_model = model or self._default_model
        if "gemini" in use_model.lower():
            use_model = "mistral-small-latest"

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

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            resp = requests.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=45,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Mistral API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise RuntimeError(f"Mistral LLM generation failed: {e}") from e

    def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = requests.get(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=8,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Mistral LLM health check failed: {e}")
            return False
