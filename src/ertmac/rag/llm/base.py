"""
LLM Provider Abstract Base
===========================
Interface for all LLM providers used in RAG answer generation.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for LLM-based answer generation."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

    @abstractmethod
    def generate_answer(
        self,
        question: str,
        context: str,
        system_prompt: str = "",
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        """
        Generates an answer grounded in the provided context.

        Args:
            question: User's question.
            context: Retrieved verified document excerpts.
            system_prompt: System instruction for the LLM.
            model: Model name override.
            max_tokens: Maximum output tokens.
            temperature: Low temperature for factual answers (0.0–0.3 recommended).

        Returns:
            Generated answer string.

        Raises:
            RuntimeError: If the LLM is unavailable or generation fails.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Returns True if the LLM provider is reachable."""
        ...
