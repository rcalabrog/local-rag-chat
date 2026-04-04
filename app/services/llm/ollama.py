from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import requests

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_stream(self, prompt: str) -> Iterator[str]:
        with requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": True},
            timeout=self.timeout_seconds,
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    logger.debug("Skipping invalid Ollama chunk: %s", raw_line)
                    continue

                text = payload.get("response", "")
                if isinstance(text, str) and text:
                    yield text

                if payload.get("done") is True:
                    break
