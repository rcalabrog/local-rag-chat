from fastapi import APIRouter, HTTPException, Request, Response, status

from app.models.schemas import SessionDetail, SessionMessage, SessionSummary, SessionUpdateRequest, SourceItem
from app.services.chat_sessions import SessionRecord

router = APIRouter(tags=["sessions"])


def _to_session_summary(session: SessionRecord) -> SessionSummary:
    return SessionSummary(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _to_session_detail(session: SessionRecord) -> SessionDetail:
    return SessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            SessionMessage(
                role=message.role,
                content=message.content,
                timestamp=message.timestamp,
                sources=[
                    SourceItem(
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


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(request: Request) -> list[SessionSummary]:
    session_store = request.app.state.chat_sessions
    sessions = session_store.list_sessions()
    return [_to_session_summary(session) for session in sessions]


@router.post("/sessions", response_model=SessionDetail, status_code=status.HTTP_201_CREATED)
def create_session(request: Request) -> SessionDetail:
    session_store = request.app.state.chat_sessions
    session = session_store.create_session()
    return _to_session_detail(session)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, request: Request) -> SessionDetail:
    session_store = request.app.state.chat_sessions
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return _to_session_detail(session)


@router.patch("/sessions/{session_id}", response_model=SessionDetail)
def update_session_title(
    session_id: str,
    request_data: SessionUpdateRequest,
    request: Request,
) -> SessionDetail:
    session_store = request.app.state.chat_sessions
    session = session_store.update_title(session_id=session_id, title=request_data.title)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return _to_session_detail(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, request: Request) -> Response:
    session_store = request.app.state.chat_sessions
    deleted = session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
