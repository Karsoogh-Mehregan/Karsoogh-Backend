from django.db import models

# Create your models here.
#
class ExamSession(models.Model):
    name = models.CharField()



class SubmissionFile(models.Model):
    name = models.CharField()