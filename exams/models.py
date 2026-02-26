from django.db import models

class QuestionModel(models.Model):
    sign_name=models.CharField(max_length=31, help_text="a name to know what this question is")
    # question_picture=models.ImageField(upload_to="dirQuestions")
    exam = models.ForeignKey("ExamModel", on_delete=models.CASCADE, related_name="questions", null=True, blank=True)
    def __str__(self):
        return self.sign_name
    
class ExamModel(models.Model):
    name=models.CharField(max_length=63, unique=True)
    start_time=models.DateTimeField()
    end_time=models.DateTimeField()
    is_visible=models.BooleanField()
    def __str__(self):
        return f"{self.id}_{self.name}"
