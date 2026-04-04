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

    def event_stream() -> Iterator[str]:
        try:
            token_stream, sources = rag_pipeline.stream_answer(request_data.question)
            for token in token_stream:
                payload = {"type": "token", "content": token}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("Chat stream pipeline execution failed")
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

    try:
        answer, sources = rag_pipeline.answer(request_data.question)
    except Exception as exc:
        logger.exception("Chat pipeline execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response.",
        ) from exc

    return ChatResponse(answer=answer, sources=sources)
