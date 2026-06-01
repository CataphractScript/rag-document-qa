"""
Document service layer.

Responsibilities:
- Parse text from .docx files
- Index document content into the FAISS vector store
- Remove documents from the vector store on deletion

The vector store is a FAISS index persisted to disk (via Docker volume),
so embeddings survive container restarts.
"""

import logging
import os

from docx import Document as DocxDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model (loaded once, shared across the process)
# ---------------------------------------------------------------------------

_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Lazily load the embedding model (cached in module scope)."""
    global _embeddings
    if _embeddings is None:
        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding model loaded.")
    return _embeddings


# ---------------------------------------------------------------------------
# Vector store helpers
# ---------------------------------------------------------------------------

VECTOR_STORE_PATH = settings.VECTOR_STORE_PATH


def _load_or_create_vector_store() -> FAISS | None:
    """
    Load existing FAISS index from disk, or return None if it doesn't exist yet.
    """
    index_file = os.path.join(VECTOR_STORE_PATH, "index.faiss")
    if os.path.exists(index_file):
        try:
            logger.debug("Loading existing FAISS index from %s", VECTOR_STORE_PATH)
            return FAISS.load_local(
                VECTOR_STORE_PATH,
                get_embeddings(),
                allow_dangerous_deserialization=True,
            )
        except Exception as exc:
            logger.warning("Failed to load FAISS index: %s. Will rebuild.", exc)
    return None


def _save_vector_store(store: FAISS) -> None:
    """Persist the FAISS index to disk."""
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    store.save_local(VECTOR_STORE_PATH)
    logger.debug("FAISS index saved to %s", VECTOR_STORE_PATH)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract all paragraph text from a .docx file.
    Returns the combined text as a single string.
    """
    try:
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        logger.info("Extracted %d characters from %s", len(text), file_path)
        return text
    except Exception as exc:
        logger.error("Failed to extract text from %s: %s", file_path, exc)
        raise ValueError(f"Could not parse .docx file: {exc}") from exc


def index_document(document) -> None:
    """
    Chunk the document's content and add it to the FAISS vector store.
    Each chunk is tagged with the document's id and title as metadata,
    so we can trace retrieved chunks back to their source.
    """
    if not document.content.strip():
        logger.warning("Document %d has empty content; skipping indexing.", document.id)
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(document.content)
    if not chunks:
        logger.warning("No chunks produced for document %d.", document.id)
        return

    metadatas = [
        {"document_id": document.id, "document_title": document.title, "chunk_index": i}
        for i, _ in enumerate(chunks)
    ]

    store = _load_or_create_vector_store()
    if store is None:
        # First document — create a new index
        store = FAISS.from_texts(chunks, get_embeddings(), metadatas=metadatas)
    else:
        store.add_texts(chunks, metadatas=metadatas)

    _save_vector_store(store)
    logger.info("Indexed %d chunks for document '%s' (id=%d).", len(chunks), document.title, document.id)


def remove_document_from_index(document_id: int) -> None:
    """
    Remove all chunks belonging to a document from the FAISS index.
    FAISS doesn't support deletion natively, so we rebuild the index
    from the remaining documents.
    """
    store = _load_or_create_vector_store()
    if store is None:
        return  # Nothing to remove

    # Collect ids of vectors that belong to this document
    ids_to_delete = [
        doc_id
        for doc_id, doc in store.docstore._dict.items()
        if doc.metadata.get("document_id") == document_id
    ]

    if not ids_to_delete:
        logger.info("No vectors found for document_id=%d; nothing to remove.", document_id)
        return

    store.delete(ids_to_delete)
    _save_vector_store(store)
    logger.info("Removed %d vectors for document_id=%d.", len(ids_to_delete), document_id)


def reindex_all_documents() -> None:
    """
    Rebuild the entire vector store from all documents currently in the DB.
    Used by the management command `index_documents`.
    """
    from documents.models import Document

    # Wipe existing index
    import shutil
    if os.path.exists(VECTOR_STORE_PATH):
        shutil.rmtree(VECTOR_STORE_PATH)
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)

    documents = Document.objects.all()
    if not documents.exists():
        logger.info("No documents to index.")
        return

    all_texts = []
    all_metadatas = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    for doc in documents:
        if not doc.content.strip():
            continue
        chunks = splitter.split_text(doc.content)
        for i, chunk in enumerate(chunks):
            all_texts.append(chunk)
            all_metadatas.append({
                "document_id": doc.id,
                "document_title": doc.title,
                "chunk_index": i,
            })

    if all_texts:
        store = FAISS.from_texts(all_texts, get_embeddings(), metadatas=all_metadatas)
        _save_vector_store(store)
        logger.info("Reindexed %d total chunks from %d documents.", len(all_texts), documents.count())
    else:
        logger.info("All documents had empty content; index not created.")
