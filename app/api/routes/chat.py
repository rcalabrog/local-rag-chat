import logging
import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat_stream(request_data: ChatRequest, request: Request) -> StreamingResponse:
    rag_pipeline = request.app.state.rag_pipeline
    chat_sessions = request.app.state.chat_sessions

    existing_session = chat_sessions.get_session(request_data.session_id)
    if existing_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    persisted_user = chat_sessions.append_message(
        session_id=request_data.session_id,
        role="user",
        content=request_data.question,
    )
    if persisted_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    def event_stream() -> Iterator[str]:
        assistant_parts: list[str] = []
        final_sources: list[dict[str, object]] = []
        try:
            token_stream, sources = rag_pipeline.stream_answer(
                request_data.question,
                active_documents=request_data.active_documents,
            )
            final_sources = sources
            for token in token_stream:
                assistant_parts.append(token)
                payload = {"type": "token", "content": token}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            assistant_content = "".join(assistant_parts).strip() or "I don't know"
            chat_sessions.append_message(
                session_id=request_data.session_id,
                role="assistant",
                content=assistant_content,
                sources=final_sources,
            )
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Chat stream pipeline execution failed")
            if not assistant_parts:
                chat_sessions.append_message(
                    session_id=request_data.session_id,
                    role="assistant",
                    content="I don't know",
                    sources=[],
                )
            error_payload = {"type": "error", "message": "Failed to generate response."}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/sources", response_model=ChatResponse)
def chat_with_sources(request_data: ChatRequest, request: Request) -> ChatResponse:
    rag_pipeline = request.app.state.rag_pipeline
    chat_sessions = request.app.state.chat_sessions

    existing_session = chat_sessions.get_session(request_data.session_id)
    if existing_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    persisted_user = chat_sessions.append_message(
        session_id=request_data.session_id,
        role="user",
        content=request_data.question,
    )
    if persisted_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    try:
        answer, sources = rag_pipeline.answer(
            request_data.question,
            active_documents=request_data.active_documents,
        )
        chat_sessions.append_message(
            session_id=request_data.session_id,
            role="assistant",
            content=answer,
            sources=sources,
        )
    except Exception as exc:
        logger.exception("Chat pipeline execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response.",
        ) from exc

    return ChatResponse(answer=answer, sources=sources)
