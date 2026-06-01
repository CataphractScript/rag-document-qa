from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "created_at", "updated_at"]
    list_display_links = ["id", "title"]
    search_fields = ["title", "content"]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["title", "content", "file", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        """Re-index when a document is saved via admin."""
        from documents.services import extract_text_from_docx, index_document, remove_document_from_index
        import logging
        logger = logging.getLogger(__name__)

        if change:
            remove_document_from_index(obj.id)

        super().save_model(request, obj, form, change)

        # If a new .docx was uploaded, extract text
        if obj.file and (not obj.content or obj.content == "__placeholder__"):
            try:
                obj.content = extract_text_from_docx(obj.file.path)
                obj.save(update_fields=["content"])
            except Exception as exc:
                logger.error("Admin: text extraction failed: %s", exc)

        try:
            index_document(obj)
        except Exception as exc:
            logger.error("Admin: indexing failed for document %d: %s", obj.id, exc)

    def delete_model(self, request, obj):
        from documents.services import remove_document_from_index
        remove_document_from_index(obj.id)
        super().delete_model(request, obj)
