from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader


def extract_text_from_bytes(content: bytes, filename: str, content_type: str | None = None) -> str:
    suffix = Path(filename).suffix.lower()

    if not content:
        raise ValueError("Uploaded file is empty.")

    if suffix == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        return text

    if suffix in {".txt", ".md", ".log", ".csv"} or (content_type or "").startswith("text/"):
        return content.decode("utf-8", errors="ignore").strip()

    raise ValueError("Unsupported file type. Only text and PDF files are allowed.")


async def extract_text_from_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    content = await file.read()
    return extract_text_from_bytes(content=content, filename=filename, content_type=file.content_type)
