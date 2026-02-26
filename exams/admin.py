from django.contrib import admin
from .models import ExamModel, QuestionModel

admin.site.register(ExamModel)
admin.site.register(QuestionModel)
