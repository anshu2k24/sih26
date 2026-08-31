"""
PS121 Handwritten Notes OCR — File & Image Validator
Performs strict multi-layer file validation:
1. File extension validation
2. MIME type validation
3. Magic byte signature verification
4. File size limits
5. Image dimension and integrity checks
"""

import io
import logging
from typing import Tuple, Optional, Dict, Any
from PIL import Image

logger = logging.getLogger("ertmac.notes.validator")

# Supported file signatures (magic bytes)
MAGIC_SIGNATURES = {
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # Checked with WEBP at offset 8
    "application/pdf": [b"%PDF-"],
    "image/heic": [b"ftypheic", b"ftypheix", b"ftypmif1"],  # Checked at offset 4
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MIN_DIMENSION = 50
MAX_DIMENSION = 12000


class FileValidationError(Exception):
    """Raised when an uploaded file violates security or format constraints."""
    pass


class FileValidator:
    """
    Validates uploaded handwritten notes files against security and integrity policies.
    Never trusts extension or client MIME header alone.
    """

    @classmethod
    def validate(
        cls,
        file_bytes: bytes,
        filename: str,
        max_size_bytes: int = MAX_FILE_SIZE_BYTES,
    ) -> Dict[str, Any]:
        """
        Validates file bytes and returns verified metadata.
        Raises FileValidationError if validation fails.
        """
        if not file_bytes:
            raise FileValidationError("Uploaded file is empty (0 bytes).")

        size_bytes = len(file_bytes)
        if size_bytes > max_size_bytes:
            raise FileValidationError(
                f"File size ({size_bytes / (1024*1024):.2f} MB) exceeds maximum allowed size ({max_size_bytes / (1024*1024):.1f} MB)."
            )

        # 1. Extension check
        dot_idx = filename.rfind(".")
        if dot_idx == -1:
            raise FileValidationError(f"File '{filename}' lacks a valid file extension.")
        ext = filename[dot_idx:].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"File extension '{ext}' is unsupported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # 2. Magic byte check
        detected_mime, detected_format = cls._detect_magic_bytes(file_bytes)
        if not detected_mime:
            raise FileValidationError(
                f"File contents do not match any permitted image or document signatures (Magic byte mismatch)."
            )

        # 3. Integrity & Dimension check (for images)
        dimensions: Optional[Tuple[int, int]] = None
        if detected_mime.startswith("image/"):
            try:
                with Image.open(io.BytesIO(file_bytes)) as img:
                    img.verify()  # Check for corruption
                
                # Re-open for dimension inspection after verify()
                with Image.open(io.BytesIO(file_bytes)) as img:
                    w, h = img.size
                    dimensions = (w, h)
                    if w < MIN_DIMENSION or h < MIN_DIMENSION:
                        raise FileValidationError(f"Image dimensions ({w}x{h}) are too small for OCR processing.")
                    if w > MAX_DIMENSION or h > MAX_DIMENSION:
                        raise FileValidationError(f"Image dimensions ({w}x{h}) exceed maximum permitted size ({MAX_DIMENSION}px).")
            except FileValidationError:
                raise
            except Exception as e:
                raise FileValidationError(f"Image file is corrupted or unreadable: {e}")

        return {
            "filename": filename,
            "extension": ext,
            "mime_type": detected_mime,
            "format": detected_format,
            "size_bytes": size_bytes,
            "dimensions": dimensions,
        }

    @staticmethod
    def _detect_magic_bytes(data: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Inspects binary header to determine true MIME and format."""
        if len(data) < 12:
            return None, None

        # JPEG
        if data.startswith(b"\xFF\xD8\xFF"):
            return "image/jpeg", "JPEG"

        # PNG
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png", "PNG"

        # WEBP: Starts with 'RIFF' and contains 'WEBP' at offset 8
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp", "WEBP"

        # PDF
        if data.startswith(b"%PDF-"):
            return "application/pdf", "PDF"

        # HEIC / HEIF
        if len(data) > 12 and data[4:8] == b"ftyp":
            brand = data[8:12]
            if brand in (b"heic", b"heix", b"mif1", b"msf1"):
                return "image/heic", "HEIC"

        return None, None
