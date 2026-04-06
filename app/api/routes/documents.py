import logging

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status

from app.models.schemas import ClearDocumentsResponse, UploadResponse
from app.services.vector_store import ChunkInput
from app.utils.chunking import chunk_text
from app.utils.document_loader import extract_text_from_bytes
from app.utils.hash import compute_sha256

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
) -> UploadResponse:
    settings = request.app.state.settings
    embedding_service = request.app.state.embedding_service
    vector_store = request.app.state.vector_store
    document_registry = request.app.state.document_registry

    try:
        source = file.filename or "uploaded_file"
        content = await file.read()
        file_hash = compute_sha256(content)

        if document_registry.contains_hash(file_hash):
            logger.info("Duplicate document detected for %s (hash=%s)", source, file_hash)
            response.status_code = status.HTTP_200_OK
            return UploadResponse(
                message="Document already indexed",
                filename=source,
                chunks_added=0,
                total_chunks=vector_store.size,
                already_indexed=True,
            )

        text = extract_text_from_bytes(content=content, filename=source, content_type=file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text found in the uploaded file.",
        )

    chunks = chunk_text(text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks generated from uploaded content.",
        )

    embeddings = embedding_service.embed_texts(chunks)
    chunk_records = [
        ChunkInput(text=chunk_text_value, filename=source, chunk_id=chunk_id)
        for chunk_id, chunk_text_value in enumerate(chunks, start=1)
    ]
    chunks_added = vector_store.add_chunks(chunk_records, embeddings)
    document_registry.add_document(source, file_hash)
    response.status_code = status.HTTP_201_CREATED

    logger.info("Indexed %d chunks from %s", chunks_added, source)

    return UploadResponse(
        message="Document indexed successfully.",
        filename=source,
        chunks_added=chunks_added,
        total_chunks=vector_store.size,
        already_indexed=False,
    )


@router.delete("/documents", response_model=ClearDocumentsResponse)
def clear_documents(request: Request) -> ClearDocumentsResponse:
    vector_store = request.app.state.vector_store
    document_registry = request.app.state.document_registry

    vector_store.clear()
    document_registry.clear()
    logger.info("All indexed documents were cleared.")

    return ClearDocumentsResponse(message="All documents cleared")
