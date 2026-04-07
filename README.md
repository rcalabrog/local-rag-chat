# Local RAG Chat

![Local RAG Chat Preview](frontend/public/images/localragchat_minidemo.gif)

Production-style local Retrieval-Augmented Generation (RAG) chat system with:

- Local LLM execution (Ollama)
- Multi-document RAG
- Streaming responses
- Collapsible metadata-rich sources
- Chat sessions with sidebar navigation
- Clear Data button (FAISS reset)
- `.pdf`, `.docx`, `.txt`, `.md` document ingestion support

## Features

### Chat Sessions

- Sidebar with session history
- Switch between conversations
- Persistent backend storage
- Session titles from first user message

### Document Upload

- PDF
- TXT
- MD
- DOCX support
- Duplicate protection via SHA256

### Retrieval-Augmented Generation

- FAISS vector search
- Metadata-aware chunk retrieval
- Context-based generation
- Source traceability

### Streaming UX

- Token streaming
- Smooth incremental rendering
- Thinking indicator
- ChatGPT-style interaction

### Source Transparency

- Filename
- Chunk ID
- Preview text
- Collapsible UI
- Metadata-rich display

### Data Management

- Clear Data button
- Resets FAISS index
- Clears registry
- Clears chat sessions

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
- `python-docx`  
  DOCX parsing and text extraction in the upload pipeline.
- `JSON file persistence`  
  Local persistence layer for vector metadata, dedupe registry, and chat sessions.

### Frontend

- `Next.js 16` (App Router)  
  Modern React framework with strong TypeScript and production bundling.
- `React 19`  
  Robust component model and state handling for real-time chat UX.
- `TypeScript`  
  End-to-end type safety across streaming and session/source payloads.
- `Tailwind CSS`  
  Fast, maintainable utility-based styling for product-grade UI iteration.
- `Framer Motion`  
  Smooth, declarative UI animations (typing indicator, collapsible panels, modal transitions).
- `Sidebar session UI`  
  ChatGPT-style navigation and active-session switching.
- `Modal confirmation system`  
  Safe destructive-action confirmation for Clear Data.
- `Streaming message renderer`  
  Incremental token rendering for smooth assistant output.

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
|-- app/
|   |-- api/routes/
|   |   |-- chat.py
|   |   |-- documents.py
|   |   `-- sessions.py
|   |-- core/config.py
|   |-- models/schemas.py
|   |-- services/
|   |   |-- chat_sessions.py
|   |   |-- document_registry.py
|   |   |-- embedding.py
|   |   |-- rag_pipeline.py
|   |   |-- vector_store.py
|   |   `-- llm/
|   |       |-- base.py
|   |       `-- ollama.py
|   |-- utils/
|   |   |-- chunking.py
|   |   |-- document_loader.py
|   |   `-- hash.py
|   `-- main.py
|-- data/
|   |-- vector_store/
|   |   |-- faiss.index
|   |   |-- faiss_meta.json
|   |   `-- documents.json
|   `-- chat_sessions/
|       `-- sessions.json
|-- frontend/
|   |-- app/
|   |-- components/
|   |   |-- ConfirmModal.tsx
|   |   `-- chat/
|   |       |-- chat-shell.tsx
|   |       `-- chat-sidebar.tsx
|   |-- lib/
|   `-- package.json
`-- requirements.txt
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
- `CHAT_SESSIONS_PATH` (default: `data/chat_sessions/sessions.json`)
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
- `NEXT_PUBLIC_LLM_PROVIDER` (default: `local`)
- `NEXT_PUBLIC_LLM_MODEL` (default: `llama3.1:8b`)

Example:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_LLM_PROVIDER=local
NEXT_PUBLIC_LLM_MODEL=llama3.1:8b
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

- `npm run dev` - start development server
- `npm run build` - production build
- `npm run start` - run built app
- `npm run lint` - Next lint

### Backend

No script runner file is defined; use direct commands:

- `uvicorn app.main:app --reload --port 8000`
- `python -m compileall app` (optional syntax validation)

## API Overview

### System

- `GET /health`

### Document Ingestion

- `POST /upload`
- `DELETE /documents` (Clear Data)

### Chat

- `POST /chat` (streaming SSE)
- `POST /chat/sources` (non-stream fallback)

### Sessions

- `GET /sessions`
- `POST /sessions`
- `GET /sessions/{id}`
- `DELETE /sessions/{id}`
- `PATCH /sessions/{id}` (optional title update)

## Supported File Types

- PDF
- TXT
- MD
- DOCX

DOCX files are extracted with `python-docx` by reading document paragraphs and joining non-empty text blocks before chunking/embedding.

## Chat Sessions

Chat sessions are persisted on the backend in `data/chat_sessions/sessions.json` and used as the source of truth for conversation state.

- Sidebar lists sessions ordered by most recently updated
- Users can create, switch, and delete sessions
- Active session is loaded from backend and rendered in the main panel
- Session titles are generated from the first user message
- Chat requests are session-scoped (`session_id`) so each conversation maintains isolated message history and sources

## Clear Data

The Clear Data workflow is available from the UI and guarded by a confirmation modal.

When confirmed, backend `DELETE /documents` clears:

- FAISS index file (`faiss.index`)
- Vector metadata (`faiss_meta.json`)
- Documents dedupe registry (`documents.json`)
- Chat sessions store (`data/chat_sessions/sessions.json`)

Frontend then resets local state and creates a fresh empty session.

## How RAG Works in This Project

1. Document upload (`/upload`)
2. SHA256 hash computed from file bytes
3. If hash already in registry, indexing is skipped
4. Text extraction from file (`.pdf`, `.txt`, `.md`, `.docx`)
5. Token-based chunking (size/overlap)
6. Embedding generation (`all-MiniLM-L6-v2`)
7. FAISS insertion with persisted metadata (`filename`, `chunk_id`, `text`)
8. Session-aware chat queries retrieve and filter relevant chunks
9. Prompt is built from retrieved context and streamed through Ollama
10. Assistant answer and sources are stored back into the active session

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
- Session state persists across restarts through backend JSON storage.

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
  - `chat_sessions.py`: session persistence and lifecycle
  - `llm/*`: pluggable LLM provider abstraction
- `utils/*`  
  Focused helpers:
  - file loading/parsing
  - chunking
  - hashing
- `models/schemas.py`  
  API schemas and response contracts.
- `core/config.py`  
  Environment/config management.

### Frontend layering

- `components/chat/*`  
  Chat surface components (shell, sidebar, messages, sources, typing indicator).
- `components/FileUpload.tsx` + `UploadedFileBadge.tsx`  
  Upload UX and selected-file visualization.
- `components/ConfirmModal.tsx`  
  Reusable confirmation modal for destructive actions.
- `lib/types.ts`  
  Shared TS types for stream payloads, sessions, and source metadata.
- `app/*`  
  App Router entry, global styles, metadata.

## Notes

- Persist `data/vector_store/*` and `data/chat_sessions/*` across runs if you want retrieval memory and session history to survive restarts.
- Ollama must be reachable at configured `OLLAMA_BASE_URL`.
