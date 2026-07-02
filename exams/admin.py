from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from .models import ExamModel, QuestionModel, Submission

admin.site.register(ExamModel)


@admin.register(QuestionModel)
class QuestionModelAdmin(admin.ModelAdmin):
    list_display = ("id", "sign_name", "exam", "max_grade")
    list_filter = ("exam",)
    search_fields = ("sign_name",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "grade", "uploaded_at")
    list_filter = ("question__exam", "uploaded_at")
    search_fields = ("user__username", "user__phone", "question__sign_name")
    raw_id_fields = ("user", "question")
    list_editable = ("grade",)