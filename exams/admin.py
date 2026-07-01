from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from .models import ExamModel, QuestionModel, Submission

admin.site.register(ExamModel)
admin.site.register(QuestionModel)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "uploaded_at")
    list_filter = ("question__exam", "uploaded_at")
    search_fields = ("user__username", "user__phone", "question__sign_name")
    raw_id_fields = ("user", "question")