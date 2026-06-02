import logging
import os
from typing import TypedDict

from langchain_community.vectorstores import FAISS
from openai import OpenAI
from django.conf import settings

from documents.services import get_embeddings, VECTOR_STORE_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template (plain string — no LangChain dependency needed here)
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """\
You are a helpful assistant that answers questions strictly based on the provided document context.
If the answer cannot be found in the context, say: "I could not find an answer in the provided documents."
Do NOT use any knowledge outside the context below.

--- CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer:"""


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class RAGResult(TypedDict):
    answer: str
    source_document_ids: list[int]
    source_document_titles: list[str]


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def answer_question(question: str) -> RAGResult:
    """
    Run the full RAG pipeline for the given question.

    Raises:
        ValueError: if no documents are indexed or the question is empty.
        RuntimeError: if the LLM call fails.
    """
    if not question.strip():
        raise ValueError("Question must not be empty.")

    # 1. Load vector store
    index_file = os.path.join(VECTOR_STORE_PATH, "index.faiss")
    if not os.path.exists(index_file):
        raise ValueError(
            "No documents have been indexed yet. "
            "Please add documents before asking questions."
        )

    try:
        store = FAISS.load_local(
            VECTOR_STORE_PATH,
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
    except Exception as exc:
        logger.error("Failed to load FAISS index: %s", exc)
        raise RuntimeError("Vector store could not be loaded.") from exc

    # 2. Similarity search — retrieve top-k chunks
    try:
        results = store.similarity_search(question, k=settings.RETRIEVAL_TOP_K)
    except Exception as exc:
        logger.error("Similarity search failed: %s", exc)
        raise RuntimeError("Retrieval failed.") from exc

    if not results:
        return RAGResult(
            answer="I could not find relevant information in the documents.",
            source_document_ids=[],
            source_document_titles=[],
        )

    # 3. Build context string from retrieved chunks
    context_parts = []
    seen_doc_ids: set[int] = set()
    source_titles: list[str] = []

    for doc in results:
        meta = doc.metadata
        doc_id = meta.get("document_id")
        doc_title = meta.get("document_title", "Unknown")
        context_parts.append(f"[{doc_title}]\n{doc.page_content}")
        if doc_id and doc_id not in seen_doc_ids:
            seen_doc_ids.add(doc_id)
            source_titles.append(doc_title)

    context = "\n\n".join(context_parts)

    # 4. Build prompt
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    logger.debug("Prompt length: %d chars", len(prompt))

    # 5. Call LLM via OpenRouter using the openai client directly.
    #    This avoids LangChain's ChatOpenAI wrapper which passes a 'proxies'
    #    kwarg that is no longer accepted in openai>=1.40.
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Please add it to your .env file."
        )

    try:
        client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        response = client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        raise RuntimeError(f"LLM call failed: {exc}") from exc

    logger.info(
        "Answered question (sources: %s): %s...",
        list(seen_doc_ids),
        answer[:100],
    )

    return RAGResult(
        answer=answer,
        source_document_ids=sorted(seen_doc_ids),
        source_document_titles=source_titles,
    )
