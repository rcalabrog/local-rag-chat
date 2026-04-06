from io import BytesIO
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import UploadFile
from pypdf import PdfReader


def extract_text_from_bytes(content: bytes, filename: str, content_type: str | None = None) -> str:
    suffix = Path(filename).suffix.lower()
    normalized_content_type = (content_type or "").lower()

    if not content:
        raise ValueError("Uploaded file is empty.")

    if suffix == ".pdf" or normalized_content_type == "application/pdf":
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        return text

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
