from __future__ import annotations

from functools import lru_cache
from threading import Lock
from typing import Sequence

import easyocr
import fitz
import numpy as np
from PIL import Image


class OcrService:
    _readers: dict[tuple[tuple[str, ...], bool], easyocr.Reader] = {}
    _readers_lock = Lock()

    def __init__(self, languages: Sequence[str], gpu: bool = False) -> None:
        self.languages = tuple(languages) if languages else ("en",)
        self.gpu = gpu

    def _get_reader(self) -> easyocr.Reader:
        cache_key = (self.languages, self.gpu)
        reader = self._readers.get(cache_key)
        if reader is None:
            with self._readers_lock:
                reader = self._readers.get(cache_key)
                if reader is None:
                    reader = easyocr.Reader(list(self.languages), gpu=self.gpu)
                    self._readers[cache_key] = reader
        return reader

    @staticmethod
    def _page_to_image(page: fitz.Page) -> Image.Image:
        pixmap = page.get_pixmap(alpha=False)
        mode = "L" if pixmap.n == 1 else "RGB"
        image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
        if mode == "L":
            return image.convert("RGB")
        return image

    def extract_text_from_pdf_bytes(self, content: bytes) -> str:
        reader = self._get_reader()
        page_texts: list[str] = []

        with fitz.open(stream=content, filetype="pdf") as document:
            for page in document:
                image = self._page_to_image(page)
                lines = reader.readtext(np.asarray(image), detail=0, paragraph=True)
                page_text = "\n".join(line.strip() for line in lines if isinstance(line, str) and line.strip())
                page_texts.append(page_text)

        return "\n\n".join(page_texts).strip()


@lru_cache(maxsize=8)
def get_ocr_service(languages: tuple[str, ...], gpu: bool) -> OcrService:
    return OcrService(languages=languages, gpu=gpu)
