from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Protocol, Sequence, cast

import faiss
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChunkInput:
    text: str
    filename: str
    chunk_id: int


@dataclass(slots=True)
class ChunkRecord:
    text: str
    filename: str
    chunk_id: int


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    filename: str
    chunk_id: int
    score: float


class _FaissIndexProtocol(Protocol):
    d: int
    ntotal: int

    def add(self, x: np.ndarray) -> None: ...

    def search(self, x: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]: ...


class VectorStore:
    def __init__(self, index_path: Path, metadata_path: Path) -> None:
        self.index_path = index_path
        self.metadata_path = metadata_path
        self._index: faiss.Index | None = None
        self._records: list[ChunkRecord] = []
        self._lock = RLock()

        self._ensure_paths()
        self.load_index()

    @property
    def size(self) -> int:
        return len(self._records)

    def _ensure_paths(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _parse_record(self, entry: dict[str, object], fallback_id: int) -> ChunkRecord | None:
        text = str(entry.get("text", "")).strip()
        if not text:
            return None

        filename = str(entry.get("filename") or entry.get("source") or "unknown")
        raw_chunk_id = entry.get("chunk_id", fallback_id)
        try:
            if isinstance(raw_chunk_id, int):
                chunk_id = raw_chunk_id
            elif isinstance(raw_chunk_id, float):
                chunk_id = int(raw_chunk_id)
            elif isinstance(raw_chunk_id, str):
                chunk_id = int(raw_chunk_id.strip())
            else:
                chunk_id = fallback_id
        except (TypeError, ValueError):
            chunk_id = fallback_id

        return ChunkRecord(text=text, filename=filename, chunk_id=max(chunk_id, 1))

    def load_index(self) -> None:
        with self._lock:
            self._index = None
            self._records = []
            has_index = self.index_path.exists()
            has_metadata = self.metadata_path.exists()

            if has_index != has_metadata:
                logger.warning(
                    "Incomplete vector store state detected (index=%s metadata=%s). "
                    "Starting with an empty in-memory store.",
                    has_index,
                    has_metadata,
                )

            if self.index_path.exists():
                self._index = faiss.read_index(str(self.index_path))
                logger.info("Loaded FAISS index from %s", self.index_path)

            if self.metadata_path.exists():
                raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                records_raw = raw.get("records", []) if isinstance(raw, dict) else raw
                parsed_records: list[ChunkRecord] = []
                for idx, entry in enumerate(records_raw, start=1):
                    if not isinstance(entry, dict):
                        continue
                    parsed = self._parse_record(entry, idx)
                    if parsed is not None:
                        parsed_records.append(parsed)
                self._records = parsed_records
                logger.info("Loaded %d metadata records", len(self._records))

            if self._index is not None and self._index.ntotal != len(self._records):
                expected = int(self._index.ntotal)
                logger.warning(
                    "Index/metadata mismatch detected (index=%d metadata=%d). Truncating metadata.",
                    expected,
                    len(self._records),
                )
                self._records = self._records[:expected]

    def save_index(self) -> None:
        if self._index is not None:
            faiss.write_index(self._index, str(self.index_path))

        payload = [asdict(record) for record in self._records]
        self.metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        with self._lock:
            self._index = None
            self._records = []
            removed_paths: list[str] = []

            for path in (self.index_path, self.metadata_path):
                try:
                    path.unlink()
                    removed_paths.append(str(path))
                except FileNotFoundError:
                    continue

            if removed_paths:
                logger.info("Deleted vector store files: %s", ", ".join(removed_paths))
            else:
                logger.info("Vector store files already absent; reset in-memory state only.")

    def add_chunks(self, chunks: Sequence[ChunkInput], embeddings: np.ndarray) -> int:
        if not chunks:
            return 0
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be a 2D array")
        if len(chunks) != embeddings.shape[0]:
            raise ValueError("chunks and embeddings must have the same number of rows")

        vectors = np.ascontiguousarray(embeddings, dtype=np.float32)

        with self._lock:
            if self._index is None:
                self._index = faiss.IndexFlatIP(vectors.shape[1])
                logger.info("Initialized new FAISS cosine index with dimension %d", vectors.shape[1])

            if vectors.shape[1] != self._index.d:
                raise ValueError(
                    f"Embedding dimension mismatch: index={self._index.d}, incoming={vectors.shape[1]}"
                )

            index = cast(_FaissIndexProtocol, self._index)
            index.add(vectors)
            self._records.extend(
                ChunkRecord(text=chunk.text, filename=chunk.filename, chunk_id=chunk.chunk_id) for chunk in chunks
            )
            self.save_index()

        return len(chunks)

    def add_texts(self, texts: Sequence[str], embeddings: np.ndarray, source: str) -> int:
        chunks = [ChunkInput(text=text, filename=source, chunk_id=idx) for idx, text in enumerate(texts, start=1)]
        return self.add_chunks(chunks, embeddings)

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> list[RetrievedChunk]:
        if top_k <= 0:
            return []

        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        query = np.ascontiguousarray(query_embedding, dtype=np.float32)

        with self._lock:
            if self._index is None or self._index.ntotal == 0 or not self._records:
                return []

            k = min(top_k, len(self._records))
            index = cast(_FaissIndexProtocol, self._index)
            raw_scores, indices = index.search(query, k)
            metric_type = int(getattr(self._index, "metric_type", faiss.METRIC_L2))

        results: list[RetrievedChunk] = []
        for raw_score, idx in zip(raw_scores[0], indices[0]):
            if idx < 0:
                continue
            record = self._records[int(idx)]
            if metric_type == faiss.METRIC_L2:
                score = 1.0 - (float(raw_score) / 2.0)
            else:
                score = float(raw_score)
            results.append(
                RetrievedChunk(
                    text=record.text,
                    filename=record.filename,
                    chunk_id=record.chunk_id,
                    score=score,
                )
            )

        return results
