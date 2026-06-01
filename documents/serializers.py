"""
Serializers for the Document model.
"""

from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Full serializer — used for list and detail responses."""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "title", "content", "file", "file_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at", "file_url"]
        extra_kwargs = {
            "file": {"write_only": True, "required": False},
            "content": {"required": False},
        }

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def validate(self, attrs):
        """
        Either a file (docx) or content must be provided on creation.
        On update, both are optional.
        """
        if self.instance is None:  # creation
            if not attrs.get("file") and not attrs.get("content", "").strip():
                raise serializers.ValidationError(
                    "Provide either a .docx file or text content."
                )
        return attrs

    def validate_file(self, value):
        if value and not value.name.endswith(".docx"):
            raise serializers.ValidationError("Only .docx files are supported.")
        return value


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view (no full content)."""

    class Meta:
        model = Document
        fields = ["id", "title", "created_at", "updated_at"]
