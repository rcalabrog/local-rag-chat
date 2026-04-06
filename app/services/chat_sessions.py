from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _title_from_message(message: str, max_length: int = 40) -> str:
    cleaned = " ".join(message.split()).strip()
    if not cleaned:
        return "New Chat"
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 3].rstrip()}..."


@dataclass(slots=True)
class SessionSourceRecord:
    text: str
    filename: str
    chunk_id: int


@dataclass(slots=True)
class SessionMessageRecord:
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    sources: list[SessionSourceRecord] = field(default_factory=list)


@dataclass(slots=True)
class SessionRecord:
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[SessionMessageRecord] = field(default_factory=list)


class ChatSessionStore:
    def __init__(self, sessions_path: Path) -> None:
        self.sessions_path = sessions_path
        self._lock = RLock()
        self._sessions: list[SessionRecord] = []
        self._ensure_path()
        self.load()

    def _ensure_path(self) -> None:
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)

    def _parse_source(self, entry: dict[str, object]) -> SessionSourceRecord | None:
        text = str(entry.get("text", "")).strip()
        filename = str(entry.get("filename", "")).strip()
        if not text or not filename:
            return None

        raw_chunk_id = entry.get("chunk_id", 1)
        if isinstance(raw_chunk_id, int):
            chunk_id = raw_chunk_id
        elif isinstance(raw_chunk_id, float):
            chunk_id = int(raw_chunk_id)
        elif isinstance(raw_chunk_id, str):
            try:
                chunk_id = int(raw_chunk_id.strip())
            except ValueError:
                chunk_id = 1
        else:
            chunk_id = 1

        return SessionSourceRecord(
            text=text,
            filename=filename,
            chunk_id=max(chunk_id, 1),
        )

    def _parse_message(self, entry: dict[str, object]) -> SessionMessageRecord | None:
        role = str(entry.get("role", "")).strip()
        content = str(entry.get("content", ""))
        if role == "user":
            role_value: Literal["user", "assistant"] = "user"
        elif role == "assistant":
            role_value = "assistant"
        else:
            return None

        timestamp = str(entry.get("timestamp", _utc_now_iso()))
        raw_sources = entry.get("sources", [])
        sources: list[SessionSourceRecord] = []
        if isinstance(raw_sources, list):
            for source_entry in raw_sources:
                if not isinstance(source_entry, dict):
                    continue
                parsed_source = self._parse_source(source_entry)
                if parsed_source is not None:
                    sources.append(parsed_source)

        return SessionMessageRecord(
            role=role_value,
            content=content,
            timestamp=timestamp,
            sources=sources,
        )

    def _parse_session(self, entry: dict[str, object]) -> SessionRecord | None:
        session_id = str(entry.get("id", "")).strip()
        if not session_id:
            return None

        title = str(entry.get("title", "New Chat")).strip() or "New Chat"
        created_at = str(entry.get("created_at", _utc_now_iso()))
        updated_at = str(entry.get("updated_at", created_at))
        messages: list[SessionMessageRecord] = []
        raw_messages = entry.get("messages", [])
        if isinstance(raw_messages, list):
            for raw_message in raw_messages:
                if not isinstance(raw_message, dict):
                    continue
                parsed_message = self._parse_message(raw_message)
                if parsed_message is not None:
                    messages.append(parsed_message)

        return SessionRecord(
            id=session_id,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
        )

    def _write_sessions_unlocked(self) -> None:
        payload = {"sessions": [asdict(session) for session in self._sessions]}
        self.sessions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        with self._lock:
            self._sessions = []
            if not self.sessions_path.exists():
                self._write_sessions_unlocked()
                return

            raw = json.loads(self.sessions_path.read_text(encoding="utf-8"))
            raw_sessions = raw.get("sessions", []) if isinstance(raw, dict) else []
            parsed: list[SessionRecord] = []
            for entry in raw_sessions:
                if not isinstance(entry, dict):
                    continue
                parsed_session = self._parse_session(entry)
                if parsed_session is not None:
                    parsed.append(parsed_session)
            self._sessions = parsed

    def clear(self) -> None:
        with self._lock:
            self._sessions = []
            self._write_sessions_unlocked()

    def list_sessions(self) -> list[SessionRecord]:
        with self._lock:
            ordered = sorted(self._sessions, key=lambda session: session.updated_at, reverse=True)
            return [
                SessionRecord(
                    id=session.id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    messages=[],
                )
                for session in ordered
            ]

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            for session in self._sessions:
                if session.id == session_id:
                    return SessionRecord(
                        id=session.id,
                        title=session.title,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                        messages=[
                            SessionMessageRecord(
                                role=message.role,
                                content=message.content,
                                timestamp=message.timestamp,
                                sources=[
                                    SessionSourceRecord(
                                        text=source.text,
                                        filename=source.filename,
                                        chunk_id=source.chunk_id,
                                    )
                                    for source in message.sources
                                ],
                            )
                            for message in session.messages
                        ],
                    )
            return None

    def create_session(self, title: str | None = None) -> SessionRecord:
        with self._lock:
            now = _utc_now_iso()
            session = SessionRecord(
                id=str(uuid4()),
                title=(title or "New Chat").strip() or "New Chat",
                created_at=now,
                updated_at=now,
                messages=[],
            )
            self._sessions.append(session)
            self._write_sessions_unlocked()
            return SessionRecord(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
                messages=[],
            )

    def update_title(self, session_id: str, title: str) -> SessionRecord | None:
        with self._lock:
            for session in self._sessions:
                if session.id != session_id:
                    continue
                session.title = title.strip() or session.title
                session.updated_at = _utc_now_iso()
                self._write_sessions_unlocked()
                return SessionRecord(
                    id=session.id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    messages=[
                        SessionMessageRecord(
                            role=message.role,
                            content=message.content,
                            timestamp=message.timestamp,
                            sources=[
                                SessionSourceRecord(
                                    text=source.text,
                                    filename=source.filename,
                                    chunk_id=source.chunk_id,
                                )
                                for source in message.sources
                            ],
                        )
                        for message in session.messages
                    ],
                )
            return None

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            before = len(self._sessions)
            self._sessions = [session for session in self._sessions if session.id != session_id]
            deleted = len(self._sessions) != before
            if deleted:
                self._write_sessions_unlocked()
            return deleted

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list[dict[str, object]] | None = None,
    ) -> SessionRecord | None:
        if role == "user":
            role_value: Literal["user", "assistant"] = "user"
        elif role == "assistant":
            role_value = "assistant"
        else:
            raise ValueError("Invalid role")

        with self._lock:
            for session in self._sessions:
                if session.id != session_id:
                    continue

                source_records: list[SessionSourceRecord] = []
                for source in sources or []:
                    parsed = self._parse_source(source)
                    if parsed is not None:
                        source_records.append(parsed)

                message = SessionMessageRecord(
                    role=role_value,
                    content=content,
                    timestamp=_utc_now_iso(),
                    sources=source_records,
                )
                session.messages.append(message)

                if role_value == "user":
                    has_user_messages = sum(1 for item in session.messages if item.role == "user")
                    if has_user_messages == 1:
                        session.title = _title_from_message(content)

                session.updated_at = _utc_now_iso()
                self._write_sessions_unlocked()
                return SessionRecord(
                    id=session.id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    messages=[
                        SessionMessageRecord(
                            role=item.role,
                            content=item.content,
                            timestamp=item.timestamp,
                            sources=[
                                SessionSourceRecord(
                                    text=source.text,
                                    filename=source.filename,
                                    chunk_id=source.chunk_id,
                                )
                                for source in item.sources
                            ],
                        )
                        for item in session.messages
                    ],
                )
            return None
