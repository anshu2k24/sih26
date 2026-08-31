"""
PS121 Handwritten Notes OCR — Provider Unit Tests
Tests OCRProvider interface contracts, MockOCRProvider determinism, and MistralOCRProvider structure.
"""

import pytest
import asyncio
from ertmac.ocr.provider import OCRProvider
from ertmac.ocr.result import OCRInput, OCRResult, ConfidenceLevel
from ertmac.ocr.providers.mock import MockOCRProvider
from ertmac.ocr.providers.mistral import MistralOCRProvider
from ertmac.ocr.preprocessor import ImagePreprocessor
from ertmac.ocr.service import OCRService


class TestOCRProviders:

    def test_mock_provider_contracts(self):
        async def _run():
            mock_provider = MockOCRProvider(simulated_delay_ms=0)
            assert mock_provider.provider_name == "mock"
            assert await mock_provider.health_check() is True

            fake_img = b"SAMPLE_IMAGE_BYTES_FOR_DETERMINISTIC_TESTING_123"
            ocr_input = OCRInput(
                image_bytes=fake_img,
                mime_type="image/jpeg",
                filename="field_handwritten_note.jpg",
            )

            result = await mock_provider.extract_text(ocr_input)
            assert isinstance(result, OCRResult)
            assert result.provider == "mock"
            assert len(result.raw_text) > 30
            assert result.normalized_text == result.raw_text.strip()
            assert result.confidence == 0.94
            assert result.confidence_level == ConfidenceLevel.HIGH
            assert len(result.blocks) > 0
            assert "mock_mode" in result.metadata

        asyncio.run(_run())

    def test_mistral_provider_contract_and_health_check_without_key(self):
        async def _run():
            provider = MistralOCRProvider(api_key="")
            assert provider.provider_name == "mistral"
            assert provider.default_model == "mistral-ocr-latest"
            assert await provider.health_check() is False

            ocr_input = OCRInput(image_bytes=b"dummy", mime_type="image/jpeg", filename="test.jpg")
            with pytest.raises(ValueError, match="MISTRAL_API_KEY is not configured"):
                await provider.extract_text(ocr_input)

        asyncio.run(_run())

    def test_image_preprocessor_pipeline(self):
        from tests.test_file_validation import create_test_image
        raw_jpeg = create_test_image("JPEG", (1200, 900))
        
        preprocessor = ImagePreprocessor(max_dimension=1000, enhance_contrast=True)
        processed_bytes, meta = preprocessor.process(raw_jpeg)

        assert isinstance(processed_bytes, bytes)
        assert len(processed_bytes) > 0
        assert meta["original_dimensions"] == [1200, 900]
        assert meta["final_dimensions"][0] <= 1000
        assert "operations_applied" in meta

    def test_ocr_service_orchestration(self):
        async def _run():
            from tests.test_file_validation import create_test_image
            mock_provider = MockOCRProvider(simulated_delay_ms=0)
            service = OCRService(provider=mock_provider)

            test_img = create_test_image("JPEG", (500, 400))
            result = await service.process_image(test_img, "test_note.jpg")

            assert result.provider == "mock"
            assert "preprocessing" in result.metadata
            assert len(result.normalized_text) > 0

            health = await service.health_check()
            assert health["status"] == "HEALTHY"
            assert health["healthy"] is True

        asyncio.run(_run())
