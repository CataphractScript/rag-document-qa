from rest_framework import serializers
from .models import QuestionAnswer


class AskSerializer(serializers.Serializer):
    """Input serializer for the /api/ask/ endpoint."""
    question = serializers.CharField(min_length=3, max_length=1000)


class QuestionAnswerSerializer(serializers.ModelSerializer):
    """Serializer for Q&A history records."""

    sources = serializers.SerializerMethodField()

    class Meta:
        model = QuestionAnswer
        fields = ["id", "question", "answer", "sources", "created_at"]
        read_only_fields = fields

    def get_sources(self, obj):
        return [
            {"id": doc.id, "title": doc.title}
            for doc in obj.source_documents.all()
        ]
