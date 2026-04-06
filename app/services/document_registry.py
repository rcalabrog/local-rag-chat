from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock


@dataclass(slots=True)
class DocumentRecord:
    filename: str
    hash: str


class DocumentRegistry:
    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        self._lock = RLock()
        self._documents: list[DocumentRecord] = []
        self._ensure_path()
        self.load()

    def _ensure_path(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> None:
        with self._lock:
            self._documents = []
            if not self.registry_path.exists():
                self.save()
                return

            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            records = raw.get("documents", [])
            self._documents = [DocumentRecord(**record) for record in records]

    def save(self) -> None:
        with self._lock:
            payload = {"documents": [asdict(record) for record in self._documents]}
            self.registry_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def contains_hash(self, content_hash: str) -> bool:
        with self._lock:
            return any(record.hash == content_hash for record in self._documents)

    def add_document(self, filename: str, content_hash: str) -> bool:
        with self._lock:
            if any(record.hash == content_hash for record in self._documents):
                return False
            self._documents.append(DocumentRecord(filename=filename, hash=content_hash))
            payload = {"documents": [asdict(record) for record in self._documents]}
            self.registry_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return True

    def clear(self) -> None:
        with self._lock:
            self._documents = []
            payload = {"documents": []}
            self.registry_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
