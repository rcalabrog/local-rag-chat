from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local RAG Chat API"
    log_level: str = "INFO"

    chunk_size: int = Field(default=500, ge=64)
    chunk_overlap: int = Field(default=50, ge=0)
    retrieval_top_k: int = Field(default=3, ge=1)

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    vector_index_path: Path = Path("data/vector_store/faiss.index")
    vector_metadata_path: Path = Path("data/vector_store/faiss_meta.json")
    documents_registry_path: Path = Path("data/vector_store/documents.json")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = Field(default=120, ge=1)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
