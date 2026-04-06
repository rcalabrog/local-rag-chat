import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.sessions import router as sessions_router
from app.core.config import get_settings
from app.models.schemas import HealthResponse
from app.services.chat_sessions import ChatSessionStore
from app.services.document_registry import DocumentRegistry
from app.services.embedding import get_embedding_service
from app.services.llm.ollama import OllamaProvider
from app.services.rag_pipeline import RAGPipeline
from app.services.vector_store import VectorStore


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    embedding_service = get_embedding_service(settings.embedding_model_name)
    vector_store = VectorStore(settings.vector_index_path, settings.vector_metadata_path)
    document_registry = DocumentRegistry(settings.documents_registry_path)
    chat_sessions = ChatSessionStore(settings.chat_sessions_path)
    llm_provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    rag_pipeline = RAGPipeline(
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_provider=llm_provider,
        top_k=settings.retrieval_top_k,
    )

    app.state.settings = settings
    app.state.embedding_service = embedding_service
    app.state.vector_store = vector_store
    app.state.document_registry = document_registry
    app.state.chat_sessions = chat_sessions
    app.state.llm_provider = llm_provider
    app.state.rag_pipeline = rag_pipeline

    app.include_router(documents_router)
    app.include_router(sessions_router)
    app.include_router(chat_router)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
