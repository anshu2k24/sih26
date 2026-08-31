"""
Embedding Provider Abstract Base
=================================
All embedding providers must implement this interface.
This allows future replacement without rewriting the retrieval system.

Selected default provider:
    sentence-transformers / all-MiniLM-L6-v2
    - 384 dimensions
    - Free, local, no API key
    - Works offline (hackathon deployable)
    - Good semantic quality for technical text
    - pip install sentence-transformers
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """The dimension of embedding vectors produced by this provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name for logging and health checks."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single text string into a vector.

        Args:
            text: The text to embed. Should be non-empty.

        Returns:
            A list of floats with length == self.dimension

        Raises:
            RuntimeError: if the provider is unavailable or embedding fails.
        """
        ...

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-embeds multiple texts efficiently.

        Args:
            texts: List of non-empty strings to embed.

        Returns:
            List of embedding vectors, one per input text, same order.

        Raises:
            RuntimeError: if the provider is unavailable or embedding fails.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """
        Tests that the embedding provider is available and functional.

        Returns:
            True if the provider can produce embeddings, False otherwise.
        """
        ...
