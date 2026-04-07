from io import BytesIO
import logging
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import UploadFile
from pypdf import PdfReader

from app.core.config import get_settings
from app.services.ocr import get_ocr_service

logger = logging.getLogger(__name__)


def _extract_pdf_text_with_pypdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_text_from_bytes(content: bytes, filename: str, content_type: str | None = None) -> str:
    suffix = Path(filename).suffix.lower()
    normalized_content_type = (content_type or "").lower()

    if not content:
        raise ValueError("Uploaded file is empty.")

    if suffix == ".pdf" or normalized_content_type == "application/pdf":
        settings = get_settings()
        min_pdf_text_length = settings.pdf_ocr_min_text_length
        languages = tuple(settings.ocr_languages) if settings.ocr_languages else ("en",)

        pypdf_text = ""
        pypdf_error: Exception | None = None
        try:
            pypdf_text = _extract_pdf_text_with_pypdf(content)
        except Exception as exc:  # pragma: no cover - depends on malformed input files
            pypdf_error = exc

        if pypdf_text and len(pypdf_text.strip()) >= min_pdf_text_length:
            logger.info("normal PDF extraction used for %s", filename)
            return pypdf_text

        logger.info("OCR fallback triggered for %s", filename)
        try:
            ocr_service = get_ocr_service(languages=languages, gpu=settings.ocr_gpu)
            ocr_text = ocr_service.extract_text_from_pdf_bytes(content)
        except Exception as exc:
            logger.warning("OCR fallback failed for %s", filename)
            raise ValueError(
                "Unable to extract readable text from this PDF. Please upload a text-based PDF or a clearer scan."
            ) from exc

        if not ocr_text.strip():
            logger.warning("OCR fallback failed for %s", filename)
            raise ValueError(
                "Unable to extract readable text from this PDF. Please upload a text-based PDF or a clearer scan."
            ) from (pypdf_error or ValueError("OCR produced empty output"))

        logger.info("OCR fallback succeeded for %s", filename)
        return ocr_text

    if suffix == ".docx" or normalized_content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        try:
            doc = Document(BytesIO(content))
        except (PackageNotFoundError, ValueError, TypeError) as exc:
            raise ValueError("Failed to parse DOCX file.") from exc

        paragraphs = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
        extracted = "\n".join(paragraphs).strip()
        if not extracted:
            raise ValueError("DOCX file contains no extractable text.")
        return extracted

    if suffix in {".txt", ".md", ".log", ".csv"} or normalized_content_type.startswith("text/"):
        return content.decode("utf-8", errors="ignore").strip()

    raise ValueError("Unsupported file type. Only PDF, DOCX, and text files are allowed.")


async def extract_text_from_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    content = await file.read()
    return extract_text_from_bytes(content=content, filename=filename, content_type=file.content_type)
