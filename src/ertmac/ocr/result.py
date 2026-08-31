"""
PS121 Handwritten Notes OCR — Result & Input Data Contracts
Defines typed contracts for OCR input, raw results, line/word blocks, and confidence.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass
class OCRWord:
    text: str
    confidence: Optional[float] = None
    bounding_box: Optional[BoundingBox] = None


@dataclass
class OCRLine:
    text: str
    confidence: Optional[float] = None
    bounding_box: Optional[BoundingBox] = None
    words: List[OCRWord] = field(default_factory=list)


@dataclass
class OCRBlock:
    block_type: str  # "paragraph", "table", "header", "list"
    text: str
    confidence: Optional[float] = None
    lines: List[OCRLine] = field(default_factory=list)


@dataclass
class OCRInput:
    image_bytes: bytes
    mime_type: str
    filename: str
    language_hint: Optional[str] = "en"
    preprocess_options: Optional[Dict[str, Any]] = None


@dataclass
class OCRResult:
    provider: str
    model: str
    raw_text: str
    normalized_text: str
    confidence: Optional[float] = None  # Overall confidence score (0.0 to 1.0) if supported
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    processing_time_ms: int = 0
    blocks: List[OCRBlock] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "processing_time_ms": self.processing_time_ms,
            "blocks_count": len(self.blocks),
            "metadata": self.metadata,
        }
