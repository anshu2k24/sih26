"""
PS26121 eRTMAC-NWIS — Document Text Extractor
Extracts text from PDF, TXT, CSV, and DOCX files.
Provides OCR fallback using pytesseract, explicitly reporting OCR_UNAVAILABLE
if Tesseract OCR binary is not installed on the system.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger("ertmac.documents.extractor")


def extract_text_from_file(file_path: str, doc_type: str) -> Tuple[str, str, Optional[str]]:
    """
    Extracts text content from local file or Supabase Storage.

    Returns:
        (text_content, extraction_status, error_message)
        where extraction_status is 'EXTRACTED', 'OCR_REQUIRED', 'OCR_UNAVAILABLE', or 'FAILED'.
    """
    path = Path(file_path)
    temp_download = None

    if not path.exists():
        # Attempt download from Supabase Storage
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            import tempfile
            db = get_supabase_admin()
            if db:
                clean_path = file_path.replace("documents/", "")
                data = db.storage.from_("documents").download(clean_path)
                if data:
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=f".{doc_type.lower()}")
                    tfile.write(data)
                    tfile.close()
                    path = Path(tfile.name)
                    temp_download = path
        except Exception as e:
            logger.debug(f"Storage download attempt failed: {e}")

    if not path.exists():
        return "", "FAILED", f"File not found at {file_path}"

    doc_type = doc_type.upper()

    # 1. Plain Text / Markdown / Log files
    if doc_type in ("TXT", "LOG", "MD", "CSV"):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return content, "EXTRACTED", None
        except Exception as e:
            return "", "FAILED", f"Failed to read text file: {e}"

    # 2. PDF Files
    if doc_type == "PDF":
        extracted_text = ""
        try:
            # Try pypdf / PyPDF2 / pdfplumber if installed
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                for page in reader.pages:
                    txt = page.extract_text() or ""
                    extracted_text += txt + "\n"
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(str(path)) as pdf:
                        for page in pdf.pages:
                            txt = page.extract_text() or ""
                            extracted_text += txt + "\n"
                except ImportError:
                    logger.warning("Neither pypdf nor pdfplumber installed. Attempting raw text extraction.")

            if extracted_text.strip():
                return extracted_text, "EXTRACTED", None

            # If PDF yields empty text, OCR fallback is required
            logger.info(f"PDF {file_path} produced empty text — attempting Tesseract OCR fallback.")
            return _attempt_ocr_fallback(path)

        except Exception as e:
            logger.error(f"PDF text extraction error for {file_path}: {e}")
            return "", "FAILED", f"PDF extraction error: {e}"

    # 3. DOCX Files
    if doc_type in ("DOCX", "DOC"):
        try:
            import docx
            doc = docx.Document(str(path))
            full_text = [p.text for p in doc.paragraphs]
            return "\n".join(full_text), "EXTRACTED", None
        except ImportError:
            # Fallback for docx if python-docx is not installed
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                return content, "EXTRACTED", "Note: Raw text fallback used (python-docx not installed)."
            except Exception as e:
                return "", "FAILED", f"DOCX reader unavailable: {e}"
        except Exception as e:
            return "", "FAILED", f"Failed to read DOCX: {e}"

    # Fallback for unknown extensions
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return content, "EXTRACTED", None
    except Exception as e:
        return "", "FAILED", f"Unsupported document format: {doc_type}"


def _attempt_ocr_fallback(path: Path) -> Tuple[str, str, Optional[str]]:
    """
    Attempts OCR on scanned image/PDF using pytesseract.
    If Tesseract binary is not installed, returns OCR_UNAVAILABLE status.
    """
    try:
        import pytesseract
        from PIL import Image

        # Check if tesseract binary exists
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            logger.warning("Pytesseract is imported, but Tesseract-OCR binary is not installed on OS.")
            return "", "OCR_UNAVAILABLE", "PROCESSING_FAILED: OCR_UNAVAILABLE (Tesseract-OCR binary not installed on OS)"

        # Perform OCR
        img = Image.open(str(path))
        text = pytesseract.image_to_string(img)
        if text.strip():
            return text, "EXTRACTED", None
        return "", "FAILED", "OCR returned empty text"

    except ImportError:
        logger.warning("pytesseract or PIL not installed. OCR unavailable.")
        return "", "OCR_UNAVAILABLE", "PROCESSING_FAILED: OCR_UNAVAILABLE (pytesseract package not installed)"
    except Exception as e:
        logger.error(f"OCR execution error: {e}")
        return "", "OCR_UNAVAILABLE", f"PROCESSING_FAILED: OCR_UNAVAILABLE ({e})"


def check_tesseract_available() -> bool:
    """Checks if Tesseract binary is installed and executable on OS."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
