from django.contrib import admin
from .models import QuestionAnswer


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ["id", "short_question", "short_answer", "created_at"]
    list_display_links = ["id", "short_question"]
    readonly_fields = ["question", "answer", "source_documents", "created_at"]
    filter_horizontal = ["source_documents"]
    date_hierarchy = "created_at"

    def short_question(self, obj):
        return obj.question[:80]
    short_question.short_description = "Question"

    def short_answer(self, obj):
        return obj.answer[:80]
    short_answer.short_description = "Answer"
