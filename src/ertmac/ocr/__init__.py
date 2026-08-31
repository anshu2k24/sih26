"""
PS121 Handwritten Notes OCR Package
"""

from ertmac.ocr.result import (
    OCRInput,
    OCRResult,
    OCRBlock,
    OCRLine,
    OCRWord,
    ConfidenceLevel,
    BoundingBox,
)
from ertmac.ocr.provider import OCRProvider
from ertmac.ocr.preprocessor import ImagePreprocessor
from ertmac.ocr.service import OCRService, global_ocr_service

__all__ = [
    "OCRInput",
    "OCRResult",
    "OCRBlock",
    "OCRLine",
    "OCRWord",
    "ConfidenceLevel",
    "BoundingBox",
    "OCRProvider",
    "ImagePreprocessor",
    "OCRService",
    "global_ocr_service",
]
