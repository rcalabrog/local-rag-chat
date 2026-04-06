from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    active_documents: list[str] = Field(default_factory=list)


class SourceItem(BaseModel):
    text: str
    filename: str
    chunk_id: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)


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
