# Document QA System

A production-ready **Document Question-Answering system** built with Django, LangChain, FAISS, and OpenRouter. Upload `.docx` files or paste text, then ask questions — the system retrieves relevant passages using semantic search and generates accurate answers using a free LLM.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Django App                           │
│                                                             │
│  REST API (DRF)   ──▶  documents/  ──▶  FAISS Vector Store │
│                                    ──▶  SQLite DB           │
│                   ──▶  qa/         ──▶  RAG Pipeline        │
│                                         │                   │
│                                         ▼                   │
│                                    OpenRouter LLM           │
│                                  (mistral-7b-instruct:free) │
└─────────────────────────────────────────────────────────────┘
```

**RAG Flow:**
1. Document uploaded → text extracted → chunked (500 chars, 50 overlap) → embedded with `all-MiniLM-L6-v2` → stored in FAISS index (persisted to disk volume)
2. User asks question → question embedded → top-4 similar chunks retrieved → fed as context to LLM → answer returned

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- An [OpenRouter](https://openrouter.ai) API key (free tier available)

### 1. Clone the project

```bash
git clone https://github.com/CataphractScript/rag-document-qa.git
```

### 2. Set your OpenRouter API key

```bash
# Edit .env and replace the placeholder:
OPENROUTER_API_KEY=your-actual-key-here
```

You can pick any free model from https://openrouter.ai/collections/free-models.  
The default is `mistralai/mistral-7b-instruct:free`.

### 3. Start the application

```bash
docker-compose up --build
```

The first run will:
- Build the Docker image (downloads Python dependencies + embedding model ~90MB)
- Run Django migrations
- Create default admin user: `admin` / `admin123`
- Start the dev server on **http://localhost:8000**

> ⚠️ Change the admin password immediately in any non-local environment.

### 4. Access the system

| Interface | URL |
|-----------|-----|
| Django Admin | http://localhost:8000/admin/ |
| REST API | http://localhost:8000/api/ |

---

## API Documentation

### Base URL: `http://localhost:8000/api/`

---

### Documents

#### `GET /api/documents/`
List all documents (lightweight, no full content).

**Response:**
```json
[
  {
    "id": 1,
    "title": "Python Introduction",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

---

#### `POST /api/documents/`
Upload a new document. Accepts either a `.docx` file or plain text content.

**Option A — Upload .docx file (multipart/form-data):**
```bash
curl -X POST http://localhost:8000/api/documents/ \
  -F "title=My Document" \
  -F "file=@/path/to/document.docx"
```

**Option B — Plain text (JSON):**
```bash
curl -X POST http://localhost:8000/api/documents/ \
  -H "Content-Type: application/json" \
  -d '{"title": "My Document", "content": "Document text here..."}'
```

**Response (201):**
```json
{
  "id": 1,
  "title": "My Document",
  "content": "Extracted or provided text...",
  "file": null,
  "file_url": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

#### `GET /api/documents/{id}/`
Retrieve a single document with full content.

---

#### `PUT /api/documents/{id}/`
Update a document's title, content, or file.

```bash
curl -X PUT http://localhost:8000/api/documents/1/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "content": "New content..."}'
```

On update, the document is automatically re-indexed in the vector store.

---

#### `DELETE /api/documents/{id}/`
Delete a document. Also removes its vectors from the FAISS index.

```bash
curl -X DELETE http://localhost:8000/api/documents/1/
```

---

### Question Answering

#### `POST /api/ask/`
Ask a question. The system retrieves relevant chunks and generates an answer.

```bash
curl -X POST http://localhost:8000/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python used for?"}'
```

**Response (200):**
```json
{
  "answer": "Python is widely used in web development (Django, Flask), data science (pandas, NumPy), machine learning (TensorFlow, PyTorch), automation, and scripting.",
  "sources": [
    {"id": 1, "title": "Introduction to Python Programming"}
  ],
  "question_id": 42
}
```

**Error responses:**
- `400` — empty question or no documents indexed yet
- `503` — LLM unavailable or API key missing

---

### Q&A History

#### `GET /api/history/`
List all Q&A history records, newest first.

```bash
curl http://localhost:8000/api/history/
```

**Response:**
```json
[
  {
    "id": 42,
    "question": "What is Python used for?",
    "answer": "Python is widely used in...",
    "sources": [
      {"id": 1, "title": "Introduction to Python Programming"}
    ],
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

---

## Testing with Sample Data

Two sample `.docx` files are included in `sample_data/`:

| File | Content |
|------|---------|
| `python_intro.docx` | Introduction to Python programming |
| `docker_guide.docx` | Docker and containerization guide |

**Upload them:**
```bash
curl -X POST http://localhost:8000/api/documents/ \
  -F "title=Python Intro" \
  -F "file=@sample_data/python_intro.docx"

curl -X POST http://localhost:8000/api/documents/ \
  -F "title=Docker Guide" \
  -F "file=@sample_data/docker_guide.docx"
```

**Ask questions:**
```bash
curl -X POST http://localhost:8000/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I create a virtual environment in Python?"}'

curl -X POST http://localhost:8000/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a Docker volume used for?"}'
```

---

## Management Commands

```bash
# Rebuild the entire vector index from all DB documents
docker-compose exec web python manage.py index_documents

# Create default superuser (runs automatically on startup)
docker-compose exec web python manage.py create_default_superuser
```

---

## Django Admin Panel

Access at **http://localhost:8000/admin/** with credentials `admin` / `admin123`.

**Documents section:** Upload new `.docx` files or paste text directly. Documents are automatically indexed on save and de-indexed on delete.

**Q&A History section:** View all questions, answers, and which documents were used as sources.

---

## Project Structure

```
rag-document-qa/
├── config/               # Django project settings & URLs
│   ├── settings.py       # All configuration (env-var driven)
│   └── urls.py
├── documents/            # Document management app
│   ├── models.py         # Document model
│   ├── services.py       # .docx parsing + FAISS vector store management
│   ├── serializers.py
│   ├── views.py          # REST API views
│   ├── admin.py
│   └── management/commands/
│       ├── index_documents.py        # Rebuild vector index
│       └── create_default_superuser.py
├── qa/                   # Q&A app
│   ├── models.py         # QuestionAnswer history model
│   ├── rag_pipeline.py   # Core RAG logic (retrieval + LLM call)
│   ├── serializers.py
│   ├── views.py          # /api/ask/ and /api/history/ views
│   └── admin.py
├── sample_data/          # Sample .docx files for testing
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env                  # Environment variables (add your API key here)
```

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | Django secret key |
| `DEBUG` | `True` | Debug mode |
| `OPENROUTER_API_KEY` | (required) | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `mistralai/mistral-7b-instruct:free` | LLM model |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `VECTOR_STORE_PATH` | `/app/vector_store` | FAISS index location |

---

## Design Decisions

- **FAISS (in-memory + disk):** Simple, no extra service needed. The index is saved to a Docker volume so it survives restarts. Deletion is handled by rebuilding affected entries.
- **HuggingFace Embeddings (local):** `all-MiniLM-L6-v2` runs on CPU inside the container — no API key needed, keeps costs zero.
- **OpenRouter:** Provides an OpenAI-compatible API, so we use LangChain's `ChatOpenAI` with a custom `base_url`. Free models are sufficient for document QA.
- **Strict RAG:** The LLM prompt explicitly instructs the model to answer only from the provided context, preventing hallucination from outside knowledge.
- **SQLite:** Sufficient for the project scope; easy to swap for PostgreSQL by changing `DATABASES` in settings.

---

## Known Limitations

- FAISS deletion rebuilds the affected entries (not a full index rebuild, but O(n) on large datasets).
- No authentication on API endpoints (add DRF token auth for production).
- Embedding model downloads ~90MB on first container build.
