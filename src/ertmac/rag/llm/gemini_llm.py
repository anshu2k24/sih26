"""
Google Gemini LLM Provider for RAG Answer Generation
=====================================================
Uses Google Gemini API (v1beta) to generate context-grounded answers.

Configuration:
    RAG_LLM_PROVIDER=gemini
    RAG_LLM_MODEL=gemini-1.5-flash (or gemini-2.0-flash, gemini-1.5-pro)
    GEMINI_API_KEY=your-gemini-api-key  (or GOOGLE_API_KEY)
"""

import logging
import os
import requests
from typing import Optional, Dict, Any, List

from ertmac.rag.llm.base import LLMProvider

logger = logging.getLogger("ertmac.rag.llm.gemini")


class GeminiLLMProvider(LLMProvider):
    """Google Gemini completion provider for RAG Q&A."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ):
        self._api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        )
        self._default_model = (
            default_model
            or os.getenv("RAG_LLM_MODEL")
            or os.getenv("GEMINI_MODEL")
            or "gemini-3.5-flash"
        )
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return f"gemini/{self._default_model}"

    def generate_answer(
        self,
        question: str,
        context: str,
        system_prompt: str = "",
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        """Generates a grounded answer using Google Gemini generateContent."""
        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. "
                "Set GEMINI_API_KEY in your .env file."
            )

        requested_model = model or self._default_model
        if "/" in requested_model:
            requested_model = requested_model.split("/")[-1]

        candidate_models = [requested_model]
        for fallback in [
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite-preview",
            "gemini-3-flash-preview",
            "gemini-3.5-flash",
        ]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        sys_instruction = (
            system_prompt
            or (
                "You are an expert technical intelligence assistant for eRTMAC Operations. "
                "Answer questions strictly and accurately based on the provided verified context. "
                "Always cite specific document names, note IDs, and page numbers when available. "
                "If the context does not contain enough information to answer, state clearly that "
                "information is insufficient."
            )
        )

        user_content = (
            f"Verified Technical Context:\n{context}\n\n"
            f"User Question: {question}\n\n"
            "Provide a clear, accurate, and professional response grounded strictly in the context above:"
        )

        last_error = None
        for m in candidate_models:
            url = f"{self._base_url}/models/{m}:generateContent?key={self._api_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_content}]
                    }
                ],
                "systemInstruction": {
                    "parts": [{"text": sys_instruction}]
                },
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                }
            }

            try:
                resp = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=25,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                elif resp.status_code in (400, 404):
                    logger.warning(f"Gemini model '{m}' returned {resp.status_code}: {resp.text}, trying fallback...")
                    last_error = f"Gemini API error ({resp.status_code}): {resp.text}"
                    continue
                else:
                    raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            except Exception as e:
                logger.error(f"Gemini generation error with model '{m}': {e}")
                last_error = e

        # Fallback to Mistral LLM if Mistral key is configured and Gemini failed
        if os.getenv("MISTRAL_API_KEY"):
            logger.info("Gemini API call failed, falling back to Mistral LLM...")
            try:
                from ertmac.rag.llm.mistral_llm import MistralLLMProvider
                mistral = MistralLLMProvider()
                return mistral.generate_answer(
                    question=question,
                    context=context,
                    system_prompt=sys_instruction,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as m_err:
                logger.error(f"Mistral LLM fallback failed: {m_err}")

        raise RuntimeError(f"Gemini LLM generation failed: {last_error}")

    def health_check(self) -> bool:
        """Checks if Gemini API key is configured and valid."""
        if not self._api_key:
            return False
        try:
            url = f"{self._base_url}/models?key={self._api_key}"
            resp = requests.get(url, timeout=8)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
