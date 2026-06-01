"""
Document models.
A Document stores the original .docx file, its extracted text content,
and metadata. The text is indexed into the vector store for semantic search.
"""

import logging
from django.db import models

logger = logging.getLogger(__name__)


class Document(models.Model):
    """
    Represents a text document in the system.
    Supports optional .docx file upload; text can also be entered manually.
    """

    title = models.CharField(max_length=255, help_text="Human-readable title for the document.")
    content = models.TextField(help_text="Full extracted text content of the document.")
    file = models.FileField(
        upload_to="documents/",
        null=True,
        blank=True,
        help_text="Original .docx file (optional).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.title
