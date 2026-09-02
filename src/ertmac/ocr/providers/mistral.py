"""
PS121 Handwritten Notes OCR — Mistral OCR Provider
Implements state-of-the-art vision-based handwriting recognition via Mistral AI endpoints:
- Supports 'mistral-ocr-latest' and 'pixtral-12b-2409'
- Sends base64 data URI payload
- Handles API errors, timeouts, rate limits, and response parsing
"""

import os
import time
import base64
import logging
import requests
from typing import Optional, Dict, Any, List

from ertmac.ocr.provider import OCRProvider
from ertmac.ocr.result import OCRInput, OCRResult, OCRBlock, OCRLine, OCRWord, ConfidenceLevel

logger = logging.getLogger("ertmac.ocr.providers.mistral")


class MistralOCRProvider(OCRProvider):
    """
    Production-grade Mistral OCR & Vision provider for handwritten notes recognition.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "mistral-ocr-latest",
        timeout_seconds: int = 15,
        base_url: str = "https://api.mistral.ai/v1",
    ):
        self._api_key = api_key if api_key is not None else (os.getenv("MISTRAL_API_KEY") or os.getenv("OCR_API_KEY") or "")
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "mistral"

    @property
    def default_model(self) -> str:
        return self._default_model

    async def health_check(self) -> bool:
        """Checks if Mistral API key is configured and endpoint is reachable."""
        if not self._api_key:
            logger.warning("Mistral API key not configured.")
            return False
        try:
            # Check models list endpoint
            resp = requests.get(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=8,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Mistral health check failed: {e}")
            return False

    async def extract_text(self, ocr_input: OCRInput, model: Optional[str] = None) -> OCRResult:
        """
        Extracts handwritten text using Mistral OCR or Pixtral vision.
        """
        if not self._api_key:
            raise ValueError("MISTRAL_API_KEY is not configured on server.")

        selected_model = model or self._default_model
        start_time = time.time()

        # Format image as base64 data URI
        mime = ocr_input.mime_type or "image/jpeg"
        b64_img = base64.b64encode(ocr_input.image_bytes).decode("utf-8")
        data_uri = f"data:{mime};base64,{b64_img}"

        # If model is mistral-ocr-latest, try dedicated OCR endpoint first
        if "ocr" in selected_model.lower():
            try:
                return await self._call_ocr_endpoint(ocr_input, data_uri, selected_model, start_time)
            except Exception as e:
                logger.warning(f"Mistral OCR endpoint failed ({e}), falling back to Pixtral vision endpoint.")
                return await self._call_chat_vision_endpoint(ocr_input, data_uri, "pixtral-12b-2409", start_time)
        else:
            return await self._call_chat_vision_endpoint(ocr_input, data_uri, selected_model, start_time)

    async def _call_ocr_endpoint(
        self, ocr_input: OCRInput, data_uri: str, model: str, start_time: float
    ) -> OCRResult:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "document": {
                "type": "image_url",
                "image_url": data_uri,
            },
        }

        resp = requests.post(
            f"{self._base_url}/ocr",
            headers=headers,
            json=payload,
            timeout=self._timeout_seconds,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Mistral OCR API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        duration_ms = int((time.time() - start_time) * 1000)

        # Parse pages & markdown text
        raw_text_parts: List[str] = []
        blocks: List[OCRBlock] = []

        pages = data.get("pages", [])
        for page in pages:
            markdown = page.get("markdown", "")
            if markdown:
                raw_text_parts.append(markdown)
                blocks.append(
                    OCRBlock(
                        block_type="page",
                        text=markdown,
                        confidence=None,
                    )
                )

        full_raw_text = "\n\n".join(raw_text_parts) if raw_text_parts else data.get("text", "")
        normalized = full_raw_text.strip()

        return OCRResult(
            provider="mistral",
            model=model,
            raw_text=full_raw_text,
            normalized_text=normalized,
            confidence=None,  # Mistral OCR currently does not emit numeric token confidence
            confidence_level=ConfidenceLevel.HIGH if len(normalized) > 20 else ConfidenceLevel.MEDIUM,
            processing_time_ms=duration_ms,
            blocks=blocks,
            raw_response=data,
            metadata={"pages_count": len(pages), "source_filename": ocr_input.filename},
        )

    async def _call_chat_vision_endpoint(
        self, ocr_input: OCRInput, data_uri: str, model: str, start_time: float
    ) -> OCRResult:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        system_prompt = (
            "You are an expert handwriting transcription OCR system. "
            "Transcribe all handwritten and printed text in the image exactly as written. "
            "When transcribing tables, pay extremely close attention to every single cell value. "
            "Do NOT merge cells, do NOT drop numerical values (like depth, measurements, or weights). "
            "Preserve formatting, line breaks, bullet points, numbers, dates, equipment tags, and punctuation. "
            "Do NOT add conversational commentary, do NOT add introductory or concluding remarks. "
            "Output ONLY the transcribed text in valid Markdown."
        )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe the handwritten document:"},
                        {"type": "image_url", "image_url": data_uri},
                    ],
                },
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self._timeout_seconds,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Mistral Chat Vision API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        duration_ms = int((time.time() - start_time) * 1000)

        choices = data.get("choices", [])
        raw_text = choices[0]["message"]["content"] if choices else ""
        normalized = raw_text.strip()

        # Build blocks from paragraphs
        blocks = [
            OCRBlock(block_type="paragraph", text=para.strip())
            for para in normalized.split("\n\n")
            if para.strip()
        ]

        return OCRResult(
            provider="mistral",
            model=model,
            raw_text=raw_text,
            normalized_text=normalized,
            confidence=None,
            confidence_level=ConfidenceLevel.HIGH if len(normalized) > 30 else ConfidenceLevel.MEDIUM,
            processing_time_ms=duration_ms,
            blocks=blocks,
            raw_response=data,
            metadata={"usage": data.get("usage", {}), "source_filename": ocr_input.filename},
        )
