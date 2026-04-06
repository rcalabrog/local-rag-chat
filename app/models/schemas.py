from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    active_documents: list[str] = Field(default_factory=list)
    session_id: str = Field(..., min_length=1)


class SourceItem(BaseModel):
    text: str
    filename: str
    chunk_id: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)


class SessionMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    sources: list[SourceItem] = Field(default_factory=list)


class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionDetail(SessionSummary):
    messages: list[SessionMessage] = Field(default_factory=list)


class SessionUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1)


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_added: int
    total_chunks: int
    already_indexed: bool


class HealthResponse(BaseModel):
    status: str


class ClearDocumentsResponse(BaseModel):
    message: str
