"""
Document API views.

Endpoints:
  GET    /api/documents/       – list all documents (lightweight)
  POST   /api/documents/       – upload .docx or provide text
  GET    /api/documents/{id}/  – retrieve full document
  PUT    /api/documents/{id}/  – update document
  DELETE /api/documents/{id}/  – delete document
"""

import logging

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Document
from .serializers import DocumentSerializer, DocumentListSerializer
from .services import extract_text_from_docx, index_document, remove_document_from_index

logger = logging.getLogger(__name__)


class DocumentListCreateView(APIView):
    """List all documents or create a new one."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        documents = Document.objects.all()
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DocumentSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data.get("file")
        content = serializer.validated_data.get("content", "")

        # If a .docx file is provided, extract its text
        if uploaded_file:
            try:
                # Save file temporarily to extract text
                doc = serializer.save(content="__placeholder__")
                extracted = extract_text_from_docx(doc.file.path)
                doc.content = extracted
                doc.save(update_fields=["content"])
            except ValueError as exc:
                doc.delete()
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            doc = serializer.save()

        # Index the document into the vector store
        try:
            index_document(doc)
        except Exception as exc:
            logger.error("Indexing failed for document %d: %s", doc.id, exc)
            # Document is still saved; indexing can be retried via management command

        return Response(
            DocumentSerializer(doc, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    """Retrieve, update, or delete a single document."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        serializer = DocumentSerializer(doc, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        serializer = DocumentSerializer(
            doc, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data.get("file")

        if uploaded_file:
            try:
                updated_doc = serializer.save()
                extracted = extract_text_from_docx(updated_doc.file.path)
                updated_doc.content = extracted
                updated_doc.save(update_fields=["content"])
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            updated_doc = serializer.save()

        # Re-index: remove old vectors, add new ones
        try:
            remove_document_from_index(updated_doc.id)
            index_document(updated_doc)
        except Exception as exc:
            logger.error("Re-indexing failed for document %d: %s", updated_doc.id, exc)

        return Response(DocumentSerializer(updated_doc, context={"request": request}).data)

    def delete(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        doc_id = doc.id

        # Remove from vector store before deleting the DB record
        try:
            remove_document_from_index(doc_id)
        except Exception as exc:
            logger.error("Failed to remove document %d from index: %s", doc_id, exc)

        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
