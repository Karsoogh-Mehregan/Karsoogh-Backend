from django.conf import settings
from django.db import models
from accounts.models import User

class QuestionModel(models.Model):
    sign_name=models.CharField(max_length=31, help_text="a name to know what this question is")
    question_picture=models.ImageField(upload_to="dirQuestions")
    exam = models.ForeignKey("ExamModel", on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    max_grade = models.PositiveIntegerField(default=100)

    def __str__(self):
        return self.sign_name
    
class ExamModel(models.Model):
    name=models.CharField(max_length=63, unique=True)
    start_time=models.DateTimeField()
    end_time=models.DateTimeField()
    is_visible=models.BooleanField()
    def __str__(self):
        return f"{self.id}_{self.name}"


def submission_upload_path(instance, filename):
    """Organize submission files: submissions/<exam_id>/<user_id>/<filename>"""
    exam_id = instance.question.exam_id or 0
    return f"submissions/{exam_id}/{instance.user_id}/{filename}"


class Submission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    question = models.ForeignKey(
        QuestionModel,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    grader=models.ForeignKey(User,on_delete=models.SET_NULL, 
                             related_name="assigned_questions", blank=True,null=True,)
                              
    file = models.FileField(upload_to=submission_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    grade = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        unique_together = ("user", "question")

    def __str__(self):
        return f"{self.user} – {self.question} ({self.uploaded_at:%Y-%m-%d %H:%M})"