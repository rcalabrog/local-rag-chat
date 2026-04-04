from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from typing import Sequence

from app.services.embedding import EmbeddingService
from app.services.llm.base import LLMProvider
from app.services.vector_store import RetrievedChunk, VectorStore


class RAGPipeline:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        llm_provider: LLMProvider,
        top_k: int = 3,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.top_k = 3

    def _dedupe_chunks(self, chunks: Sequence[RetrievedChunk]) -> list[RetrievedChunk]:
        seen: set[tuple[str, str]] = set()
        unique_chunks: list[RetrievedChunk] = []
        for chunk in chunks:
            normalized = chunk.text.strip()
            key = (normalized, chunk.filename)
            if not normalized or key in seen:
                continue
            seen.add(key)
            unique_chunks.append(chunk)
            if len(unique_chunks) >= self.top_k:
                break
        return unique_chunks

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        query_embedding = self.embedding_service.embed_text(question)
        search_k = max(self.top_k * 3, self.top_k)
        retrieved_chunks = self.vector_store.search(query_embedding, top_k=search_k)
        return self._dedupe_chunks(retrieved_chunks)

    def _filter_active_documents(
        self,
        chunks: Sequence[RetrievedChunk],
        active_documents: Sequence[str] | None,
    ) -> list[RetrievedChunk]:
        if not active_documents:
            return list(chunks)

        active = {name.strip() for name in active_documents if name and name.strip()}
        if not active:
            return list(chunks)

        filtered = [chunk for chunk in chunks if chunk.filename in active]
        if filtered:
            return filtered

        return [chunks[0]] if chunks else []

    def build_context(self, chunks: Sequence[RetrievedChunk]) -> str:
        if not chunks:
            return "[No relevant context found]"
        return "\n".join(f"[{chunk.filename} | chunk #{chunk.chunk_id}] {chunk.text}" for chunk in chunks)

    def build_prompt(self, question: str, chunks: Sequence[RetrievedChunk]) -> str:
        context = self.build_context(chunks)

        return (
            "You are a helpful assistant that answers questions based only on the provided context.\n\n"
            "If the answer is not in the context, respond exactly with: I don't know\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{question}\n\n"
            "Answer:"
        )

    def prepare(
        self,
        question: str,
        active_documents: Sequence[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        retrieved_chunks = self.retrieve(question)
        filtered_chunks = self._filter_active_documents(retrieved_chunks, active_documents)
        prompt = self.build_prompt(question, filtered_chunks)
        sources = [
            {
                "text": chunk.text,
                "filename": chunk.filename,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in filtered_chunks
        ]
        return prompt, sources

    def stream_answer(
        self,
        question: str,
        active_documents: Sequence[str] | None = None,
    ) -> tuple[Iterator[str], list[dict[str, Any]]]:
        prompt, sources = self.prepare(question, active_documents=active_documents)
        stream = self.llm_provider.generate_stream(prompt)
        return stream, sources

    def answer(
        self,
        question: str,
        active_documents: Sequence[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        prompt, sources = self.prepare(question, active_documents=active_documents)
        answer = self.llm_provider.generate(prompt)
        return answer, sources
