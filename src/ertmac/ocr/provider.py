"""
PS121 Handwritten Notes OCR — Provider Abstract Base Interface
Enforces a pluggable architecture so providers (Mistral, Google, Azure, Mock) can be swapped seamlessly.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ertmac.ocr.result import OCRInput, OCRResult


class OCRProvider(ABC):
    """
    Abstract Base Class for OCR providers.
    Every provider must implement text extraction, health checking, and provider metadata.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the provider (e.g. 'mistral', 'mock', 'google')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier used by this provider."""
        pass

    @abstractmethod
    async def extract_text(self, ocr_input: OCRInput, model: Optional[str] = None) -> OCRResult:
        """
        Extracts handwritten and printed text from given image bytes.
        
        Args:
            ocr_input: OCRInput containing raw image bytes, MIME type, and options.
            model: Optional model override.
            
        Returns:
            OCRResult containing raw text, normalized text, confidence, blocks, and timings.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verifies API connectivity, credentials, and service availability.
        
        Returns:
            True if the provider is reachable and ready to process images.
        """
        pass
