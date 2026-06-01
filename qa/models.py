"""
QA history model.
Stores each question, the generated answer, which documents were used,
and a timestamp.
"""

from django.db import models
from documents.models import Document


class QuestionAnswer(models.Model):
    """A single Q&A interaction — question, answer, sources, timestamp."""

    question = models.TextField(help_text="The user's question.")
    answer = models.TextField(help_text="The LLM-generated answer.")
    source_documents = models.ManyToManyField(
        Document,
        blank=True,
        related_name="question_answers",
        help_text="Documents whose chunks were used as context.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Q&A Record"
        verbose_name_plural = "Q&A History"

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.question[:80]}"
