"""
PS121 Handwritten Notes OCR — Text Normalizer
Normalizes raw OCR transcriptions:
- Standardizes line breaks and whitespace
- Cleans unicode formatting anomalies (smart quotes, em-dashes, non-breaking spaces)
- Preserves paragraph hierarchy, list markers, and section delimiters
"""

import re
import unicodedata


class TextNormalizer:
    """
    Standardizes raw OCR output into clean, well-formatted UTF-8 text.
    """

    @classmethod
    def normalize(cls, raw_text: str) -> str:
        if not raw_text:
            return ""

        # 1. Unicode normalization (NFC)
        text = unicodedata.normalize("NFC", raw_text)

        # 2. Normalize smart quotes and typographic dashes
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "--")
        text = text.replace("\u00a0", " ")  # non-breaking space
        text = text.replace("\ufeff", "")   # BOM

        # 3. Standardize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Remove unprintable control characters (keep \n, \t)
        text = "".join(ch for ch in text if ch in ("\n", "\t") or unicodedata.category(ch)[0] != "C")

        # 5. Trim trailing whitespace on individual lines
        lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
        text = "\n".join(lines)

        # 6. Collapse excessive consecutive blank lines (max 2 consecutive newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
