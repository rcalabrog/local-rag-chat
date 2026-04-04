# Local RAG Chat

Production-style local Retrieval-Augmented Generation (RAG) chat system with:

- FastAPI backend (document ingestion, FAISS retrieval, Ollama streaming)
- Next.js frontend (ChatGPT-like streaming UI)
- Metadata-rich sources (`filename`, `chunk_id`)
- Duplicate document protection via SHA256 registry

## Tech Stack

### Backend

- `FastAPI`  
  High-performance async API framework with strong typing and automatic OpenAPI docs.
- `Pydantic v2` + `pydantic-settings`  
  Strict request/response validation and centralized environment-driven config.
- `sentence-transformers` (`all-MiniLM-L6-v2`)  
  Compact, fast embeddings suitable for local semantic search.
- `FAISS (faiss-cpu)`  
  Efficient in-memory/local vector indexing and similarity search with persistence.
- `Ollama` (`llama3.1:8b`)  
  Local LLM inference with token streaming via HTTP.
- `requests`  
  Lightweight, reliable Ollama API integration.
- `pypdf`  
  PDF text extraction for local document ingestion.

### Frontend

- `Next.js 16` (App Router)  
  Modern React framework with strong TypeScript and production bundling.
- `React 19`  
  Robust component model and state handling for real-time chat UX.
- `TypeScript`  
  End-to-end type safety across streaming and source metadata rendering.
- `Tailwind CSS`  
  Fast, maintainable utility-based styling for product-grade UI iteration.
- `Framer Motion`  
  Smooth, declarative UI animations (typing indicator, collapsible panels, transitions).

## Prerequisites

- Python `3.10+`
- Node.js `18+` (recommended `20+`)
- npm
- Ollama installed and running locally
- Ollama model pulled:

```bash
ollama pull llama3.1:8b
```

## Repository Structure

```text
.
├── app/
│   ├── api/routes/
│   │   ├── chat.py
│   │   └── documents.py
│   ├── core/config.py
│   ├── models/schemas.py
│   ├── services/
│   │   ├── document_registry.py
│   │   ├── embedding.py
│   │   ├── rag_pipeline.py
│   │   ├── vector_store.py
│   │   └── llm/
│   │       ├── base.py
│   │       └── ollama.py
│   ├── utils/
│   │   ├── chunking.py
│   │   ├── document_loader.py
│   │   └── hash.py
│   └── main.py
├── data/vector_store/
│   ├── faiss.index
│   ├── faiss_meta.json
│   └── documents.json
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
└── requirements.txt
```

## Installation

### 1) Backend dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Environment Variables

The backend reads `.env` in repo root (optional). Defaults are already provided in `app/core/config.py`.

### Backend (`.env` at repo root)

- `APP_NAME` (default: `Local RAG Chat API`)
- `LOG_LEVEL` (default: `INFO`)
- `CHUNK_SIZE` (default: `500`)
- `CHUNK_OVERLAP` (default: `50`)
- `RETRIEVAL_TOP_K` (default: `3`)
- `EMBEDDING_MODEL_NAME` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `VECTOR_INDEX_PATH` (default: `data/vector_store/faiss.index`)
- `VECTOR_METADATA_PATH` (default: `data/vector_store/faiss_meta.json`)
- `DOCUMENTS_REGISTRY_PATH` (default: `data/vector_store/documents.json`)
- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `llama3.1:8b`)
- `OLLAMA_TIMEOUT_SECONDS` (default: `120`)
- `CORS_ORIGINS` (JSON-like list; default allows `http://localhost:3000`)

Example:

```env
LOG_LEVEL=INFO
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### Frontend (`frontend/.env.local`)

- `NEXT_PUBLIC_API_BASE_URL` (default in code: `http://localhost:8000`)

Example:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Run Locally

### 1) Start backend

From repo root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health check:

```bash
curl http://localhost:8000/health
```

### 2) Start frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open: `http://localhost:3000`

## Available Scripts

### Frontend (`frontend/package.json`)

- `npm run dev` – start development server
- `npm run build` – production build
- `npm run start` – run built app
- `npm run lint` – Next lint

### Backend

No script runner file is defined; use direct commands:

- `uvicorn app.main:app --reload --port 8000`
- `python -m compileall app` (optional syntax validation)

## API Overview

### `POST /upload`

Uploads and indexes a document.

- Accepts file via multipart key `file`
- Extracts text (PDF + text-like files)
- Chunks text (`500` tokens, `50` overlap by default)
- Embeds chunks
- Stores vectors in FAISS + metadata file
- Uses SHA256 dedupe check via `documents.json`

Response:

```json
{
  "message": "Document indexed successfully.",
  "filename": "document.pdf",
  "chunks_added": 12,
  "total_chunks": 120,
  "already_indexed": false
}
```

If duplicate:

```json
{
  "message": "Document already indexed",
  "filename": "document.pdf",
  "chunks_added": 0,
  "total_chunks": 120,
  "already_indexed": true
}
```

### `POST /chat` (streaming)

SSE stream returning:

- token events:
  - `{"type":"token","content":"..."}`
- sources event:
  - `{"type":"sources","sources":[{"text":"...","filename":"...","chunk_id":1}]}`
- done event:
  - `{"type":"done"}`
- error event:
  - `{"type":"error","message":"..."}`

### `POST /chat/sources` (non-stream fallback)

Returns full answer + structured sources in one JSON response.

## How RAG Works in This Project

1. Document upload (`/upload`)
2. SHA256 hash computed from file bytes
3. If hash already in registry, indexing is skipped
4. Text extraction from file
5. Token-based chunking (size/overlap)
6. Embedding generation (`all-MiniLM-L6-v2`)
7. FAISS insertion (cosine style via normalized vectors + IP index)
8. Metadata persistence (`filename`, `chunk_id`, `text`)

For chat:

1. User question sent to `/chat`
2. Question embedding generated
3. Top-k candidate chunks retrieved from FAISS
4. Deduplication performed on `(text, filename)`
5. Context prompt built with metadata markers
6. Ollama generates streaming tokens
7. Frontend appends tokens incrementally (RAF buffered) for smooth UX
8. Structured source metadata displayed in collapsible source cards

## Main Runtime Behavior

- Embedding model is loaded once and reused (singleton-style cache).
- FAISS and metadata are loaded on backend startup.
- Vector index and metadata persist to disk after ingestion.
- Duplicate file ingestion is blocked by content hash.
- Chat responses stream token-by-token.
- Source cards show:
  - filename
  - chunk id
  - preview text with expand/collapse

## Software Architecture

### Backend layering

- `api/routes/*`  
  HTTP contract and error mapping.
- `services/*`  
  Core business logic:
  - `rag_pipeline.py`: retrieval + prompt composition + answer orchestration
  - `embedding.py`: model lifecycle + embedding ops
  - `vector_store.py`: FAISS operations and chunk metadata persistence
  - `document_registry.py`: dedupe registry
  - `llm/*`: pluggable LLM provider abstraction
- `utils/*`  
  Focused helpers:
  - file loading
  - chunking
  - hashing
- `models/schemas.py`  
  API schemas and response contracts.
- `core/config.py`  
  environment/config management.

### Frontend layering

- `components/chat/*`  
  Chat surface components (messages, sources panel, typing indicator).
- `components/FileUpload.tsx` + `UploadedFileBadge.tsx`  
  Upload UX and selected-file visualization.
- `lib/types.ts`  
  Shared TS types for stream payloads and source metadata.
- `app/*`  
  App Router entry, global styles, metadata.

## Notes

- The frontend accepts `.docx` in the file picker, but backend extraction currently supports PDF + text-like formats only.
- `data/vector_store/*` should be persisted across runs if you want retrieval memory to survive restarts.
- Ollama must be reachable at configured `OLLAMA_BASE_URL`.
