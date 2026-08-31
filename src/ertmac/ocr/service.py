"""
PS121 Handwritten Notes OCR — OCR Service Orchestrator
Coordinates provider selection, preprocessing, execution, and error handling.
"""

import os
import logging
from typing import Optional, Dict, Any

from ertmac.ocr.provider import OCRProvider
from ertmac.ocr.result import OCRInput, OCRResult
from ertmac.ocr.preprocessor import ImagePreprocessor
from ertmac.ocr.providers.mistral import MistralOCRProvider
from ertmac.ocr.providers.mock import MockOCRProvider

logger = logging.getLogger("ertmac.ocr.service")


class OCRService:
    """
    High-level OCR Service that orchestrates provider execution,
    non-destructive image preprocessing, and result normalization.
    """

    def __init__(
        self,
        provider: Optional[OCRProvider] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
    ):
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.provider = provider or self._init_default_provider()

    def _init_default_provider(self) -> OCRProvider:
        provider_name = (os.getenv("OCR_PROVIDER") or "mistral").lower().strip()
        default_model = os.getenv("OCR_MODEL") or "mistral-ocr-latest"
        timeout_ms = int(os.getenv("OCR_TIMEOUT_MS") or "35000")
        timeout_sec = max(5, timeout_ms // 1000)

        if provider_name == "mistral":
            api_key = os.getenv("MISTRAL_API_KEY") or os.getenv("OCR_API_KEY")
            if not api_key:
                logger.warning(
                    "OCR_PROVIDER is set to 'mistral' but MISTRAL_API_KEY is not set. "
                    "In local development, if real OCR is not configured, please set MISTRAL_API_KEY "
                    "or configure OCR_PROVIDER=mock for offline testing."
                )
            return MistralOCRProvider(
                api_key=api_key,
                default_model=default_model,
                timeout_seconds=timeout_sec,
            )
        elif provider_name == "mock":
            logger.info("Initializing MockOCRProvider for development/demo mode.")
            return MockOCRProvider(simulated_delay_ms=350, default_model=default_model)
        else:
            logger.warning(f"Unknown OCR provider '{provider_name}', defaulting to MockOCRProvider.")
            return MockOCRProvider(default_model="mock-fallback")

    async def process_image(
        self,
        image_bytes: bytes,
        filename: str,
        mime_type: str = "image/jpeg",
        preprocess_options: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> OCRResult:
        """
        Preprocesses image and executes OCR with configured provider.
        """
        # 1. Preprocessing
        processed_bytes, prep_meta = self.preprocessor.process(
            image_bytes=image_bytes,
            options=preprocess_options,
        )

        # 2. Construct OCR Input
        ocr_input = OCRInput(
            image_bytes=processed_bytes,
            mime_type="image/jpeg",
            filename=filename,
            preprocess_options=prep_meta,
        )

        # 3. Execute OCR
        result = await self.provider.extract_text(ocr_input=ocr_input, model=model)
        result.metadata["preprocessing"] = prep_meta

        return result

    async def health_check(self) -> Dict[str, Any]:
        """Returns health status of the active OCR service and provider."""
        is_healthy = await self.provider.health_check()
        return {
            "status": "HEALTHY" if is_healthy else "DEGRADED",
            "provider": self.provider.provider_name,
            "default_model": self.provider.default_model,
            "healthy": is_healthy,
        }


# Global singleton instance
global_ocr_service = OCRService()
