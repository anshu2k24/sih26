"""
PS121 Handwritten Notes OCR — Image Preprocessor
Implements non-destructive image preprocessing:
- EXIF orientation correction
- Adaptive contrast enhancement
- Optional grayscale conversion
- Subtle sharpening and noise suppression
- Dimension scaling while preserving aspect ratio
"""

import io
import logging
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

logger = logging.getLogger("ertmac.ocr.preprocessor")


class ImagePreprocessor:
    """
    Image preprocessing pipeline tailored for handwritten documents.
    Optimizes contrast, orientation, and resolution without destroying stroke nuances.
    """

    def __init__(
        self,
        max_dimension: int = 2400,
        min_dimension: int = 600,
        enhance_contrast: bool = True,
        contrast_factor: float = 1.35,
        sharpen: bool = True,
        auto_grayscale: bool = False,
    ):
        self.max_dimension = max_dimension
        self.min_dimension = min_dimension
        self.enhance_contrast = enhance_contrast
        self.contrast_factor = contrast_factor
        self.sharpen = sharpen
        self.auto_grayscale = auto_grayscale

    def process(
        self,
        image_bytes: bytes,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Executes the preprocessing pipeline on input image bytes.
        
        Returns:
            Tuple of (processed_image_bytes, metadata_dict)
        """
        opts = options or {}
        max_dim = opts.get("max_dimension", self.max_dimension)
        do_contrast = opts.get("enhance_contrast", self.enhance_contrast)
        contrast_val = opts.get("contrast_factor", self.contrast_factor)
        do_sharpen = opts.get("sharpen", self.sharpen)
        do_grayscale = opts.get("grayscale", self.auto_grayscale)

        meta: Dict[str, Any] = {
            "original_size_bytes": len(image_bytes),
            "operations_applied": [],
        }

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                meta["original_format"] = img.format
                meta["original_dimensions"] = [img.width, img.height]

                # 1. Orientation Correction using EXIF tags
                try:
                    oriented_img = ImageOps.exif_transpose(img)
                    if oriented_img is not None:
                        img = oriented_img
                        meta["operations_applied"].append("exif_orientation_correction")
                except Exception as e:
                    logger.debug(f"EXIF orientation correction skipped: {e}")

                # Ensure RGB mode (handles RGBA, Palette, Grayscale conversions properly)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                    meta["operations_applied"].append("convert_to_rgb")

                # 2. Resize / Dimension Clamping (keeps aspect ratio)
                w, h = img.size
                if max(w, h) > max_dim:
                    scale = max_dim / float(max(w, h))
                    new_w, new_h = int(w * scale), int(h * scale)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    meta["operations_applied"].append(f"resize_down_{new_w}x{new_h}")
                elif max(w, h) < self.min_dimension:
                    scale = self.min_dimension / float(max(w, h))
                    new_w, new_h = int(w * scale), int(h * scale)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    meta["operations_applied"].append(f"resize_up_{new_w}x{new_h}")

                # 3. Optional Grayscale
                if do_grayscale:
                    img = ImageOps.grayscale(img)
                    meta["operations_applied"].append("convert_to_grayscale")

                # 4. Contrast Enhancement (improves ink stroke visibility against textured/shadowed paper)
                if do_contrast:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(contrast_val)
                    meta["operations_applied"].append(f"contrast_enhance_{contrast_val}")

                # 5. Subtle Sharpening
                if do_sharpen:
                    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
                    meta["operations_applied"].append("unsharp_mask_filter")

                meta["final_dimensions"] = [img.width, img.height]

                # Output as high-quality JPEG
                out_buffer = io.BytesIO()
                # If grayscale, save as L mode JPEG, else RGB
                save_mode = "JPEG"
                img.save(out_buffer, format=save_mode, quality=92, optimize=True)
                processed_bytes = out_buffer.getvalue()
                meta["processed_size_bytes"] = len(processed_bytes)

                return processed_bytes, meta

        except Exception as e:
            logger.warning(f"Preprocessing encountered an issue, falling back to original bytes: {e}")
            meta["error"] = str(e)
            meta["fallback"] = True
            return image_bytes, meta
