from __future__ import annotations

from functools import lru_cache
from threading import Lock
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _models: dict[str, SentenceTransformer] = {}
    _models_lock = Lock()

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def _get_model(self) -> SentenceTransformer:
        model = self._models.get(self.model_name)
        if model is None:
            with self._models_lock:
                model = self._models.get(self.model_name)
                if model is None:
                    model = SentenceTransformer(self.model_name)
                    self._models[self.model_name] = model
        return model

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        model = self._get_model()
        embeddings = model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]


@lru_cache(maxsize=8)
def get_embedding_service(model_name: str) -> EmbeddingService:
    return EmbeddingService(model_name)
