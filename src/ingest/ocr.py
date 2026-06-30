"""OCR utilities.

Wraps Tesseract (via ``pytesseract``) with an optional vision-model fallback for images
where OCR returns little or no text (e.g. diagram-heavy screenshots). All heavy imports
are lazy so this module loads without Pillow/pytesseract installed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..logging_setup import get_logger

log = get_logger("ocr")


class OCREngine:
    def __init__(
        self,
        enabled: bool = True,
        tesseract_cmd: str = "",
        languages: str = "eng",
        min_pixels: int = 10000,
        vision_client: Any = None,
        vision_fallback: bool = True,
    ):
        self.enabled = enabled
        self.tesseract_cmd = tesseract_cmd
        self.languages = languages
        self.min_pixels = min_pixels
        self.vision_client = vision_client
        self.vision_fallback = vision_fallback

    @classmethod
    def from_config(cls, cfg, vision_client: Any = None) -> "OCREngine":
        return cls(
            enabled=bool(cfg.get("ocr.enabled", True)),
            tesseract_cmd=cfg.get("ocr.tesseract_cmd", "") or "",
            languages=cfg.get("ocr.languages", "eng"),
            min_pixels=int(cfg.get("ocr.min_image_pixels", 10000)),
            vision_client=vision_client,
            vision_fallback=bool(cfg.get("ocr.vision_fallback", True)),
        )

    def _tesseract(self):
        import pytesseract  # lazy

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        return pytesseract

    def pil_to_text(self, image) -> str:
        """OCR a PIL image. Returns '' on failure or for images below the size threshold."""
        if not self.enabled:
            return ""
        try:
            if (image.width * image.height) < self.min_pixels:
                return ""
            pytesseract = self._tesseract()
            return pytesseract.image_to_string(image, lang=self.languages).strip()
        except Exception as exc:  # pragma: no cover - depends on system Tesseract
            log.warning("Tesseract OCR failed: %s", exc)
            return ""

    def file_to_text(self, image_path: str | Path) -> str:
        """OCR an image file, optionally falling back to the vision model."""
        if not self.enabled:
            return ""
        text = ""
        try:
            from PIL import Image  # lazy

            with Image.open(image_path) as image:
                text = self.pil_to_text(image)
        except Exception as exc:
            log.warning("Could not open image %s: %s", image_path, exc)

        if self._needs_vision(text) and self.vision_fallback and self.vision_client:
            try:
                described = self.vision_client.describe_image(image_path)
                if described:
                    text = (text + "\n" + described).strip() if text else described.strip()
            except Exception as exc:
                log.warning("Vision fallback failed for %s: %s", image_path, exc)
        return text

    @staticmethod
    def _needs_vision(text: str) -> bool:
        return len(text.split()) < 5
