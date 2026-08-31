"""
PS121 Handwritten Notes OCR — File Validation Test Suite
Tests magic byte verification, MIME detection, dimension limits, and corruption defense.
"""

import io
import pytest
from PIL import Image
from ertmac.notes.validator import FileValidator, FileValidationError


def create_test_image(format="JPEG", size=(400, 300), color="white") -> bytes:
    """Helper to generate valid in-memory test images."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


class TestFileValidation:

    def test_valid_jpeg_validation(self):
        jpeg_bytes = create_test_image("JPEG", (600, 400))
        result = FileValidator.validate(jpeg_bytes, "shift_note.jpg")
        assert result["extension"] == ".jpg"
        assert result["mime_type"] == "image/jpeg"
        assert result["format"] == "JPEG"
        assert result["dimensions"] == (600, 400)
        assert result["size_bytes"] == len(jpeg_bytes)

    def test_valid_png_validation(self):
        png_bytes = create_test_image("PNG", (800, 600))
        result = FileValidator.validate(png_bytes, "inspection_sheet.png")
        assert result["extension"] == ".png"
        assert result["mime_type"] == "image/png"
        assert result["format"] == "PNG"
        assert result["dimensions"] == (800, 600)

    def test_empty_file_rejected(self):
        with pytest.raises(FileValidationError, match="empty"):
            FileValidator.validate(b"", "empty.jpg")

    def test_unsupported_extension_rejected(self):
        jpeg_bytes = create_test_image("JPEG")
        with pytest.raises(FileValidationError, match="unsupported"):
            FileValidator.validate(jpeg_bytes, "document.exe")

    def test_fake_extension_magic_byte_mismatch(self):
        # Text file masquerading as .jpg
        fake_bytes = b"This is just plain text, not a real JPEG image file!"
        with pytest.raises(FileValidationError, match="Magic byte mismatch"):
            FileValidator.validate(fake_bytes, "fake_image.jpg")

    def test_oversized_file_rejected(self):
        small_limit = 1024  # 1 KB limit
        jpeg_bytes = create_test_image("JPEG", (800, 800))
        with pytest.raises(FileValidationError, match="exceeds maximum"):
            FileValidator.validate(jpeg_bytes, "large.jpg", max_size_bytes=small_limit)

    def test_undersized_image_dimensions_rejected(self):
        # 10x10 px is too tiny for OCR
        tiny_bytes = create_test_image("JPEG", (10, 10))
        with pytest.raises(FileValidationError, match="too small"):
            FileValidator.validate(tiny_bytes, "tiny.jpg")

    def test_valid_pdf_magic_bytes(self):
        fake_pdf = b"%PDF-1.5 \n%binary data stream..."
        result = FileValidator.validate(fake_pdf, "scanned_doc.pdf")
        assert result["mime_type"] == "application/pdf"
        assert result["format"] == "PDF"
