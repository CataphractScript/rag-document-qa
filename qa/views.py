"""
QA API views.

Endpoints:
  POST /api/ask/     – ask a question, get an answer from the RAG pipeline
  GET  /api/history/ – list all Q&A history records
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from documents.models import Document

from .models import QuestionAnswer
from .serializers import AskSerializer, QuestionAnswerSerializer
from .rag_pipeline import answer_question

logger = logging.getLogger(__name__)


class AskView(APIView):
    """
    POST /api/ask/
    Body: { "question": "..." }
    Returns: { "answer": "...", "sources": [...], "question_id": ... }
    """

    def post(self, request):
        serializer = AskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        question = serializer.validated_data["question"]

        try:
            result = answer_question(question)
        except ValueError as exc:
            # No documents indexed, empty question, etc.
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            # LLM or retrieval failure
            logger.error("RAG pipeline error: %s", exc)
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Persist Q&A record
        qa_record = QuestionAnswer.objects.create(
            question=question,
            answer=result["answer"],
        )
        # Link source documents
        source_ids = result["source_document_ids"]
        if source_ids:
            docs = Document.objects.filter(id__in=source_ids)
            qa_record.source_documents.set(docs)

        return Response(
            {
                "answer": result["answer"],
                "sources": [
                    {"id": doc_id, "title": title}
                    for doc_id, title in zip(
                        result["source_document_ids"],
                        result["source_document_titles"],
                    )
                ],
                "question_id": qa_record.id,
            },
            status=status.HTTP_200_OK,
        )


class HistoryView(APIView):
    """
    GET /api/history/
    Returns all Q&A history records, newest first.
    """

    def get(self, request):
        records = QuestionAnswer.objects.prefetch_related("source_documents").all()
        serializer = QuestionAnswerSerializer(records, many=True)
        return Response(serializer.data)
