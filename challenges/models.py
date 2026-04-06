from django.db import models
from django.utils import timezone
from ckeditor.fields import RichTextField
from django.db.models import Q

class ChallengeQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            Q(is_active=WeeklyChallenge.ActiveOptions.ACTIVE) |
            Q(
                is_active=WeeklyChallenge.ActiveOptions.AUTO,
                start_date__lte=now,
                end_date__gte=now
            )
        )

class WeeklyChallenge(models.Model):
    class ActiveOptions(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        AUTO = 'auto', 'Auto'

    validation_regex = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = RichTextField();
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.CharField(max_length=10, choices=ActiveOptions.choices, default=ActiveOptions.AUTO)
    created_at = models.DateTimeField(auto_now_add=True)


    objects = ChallengeQuerySet.as_manager()
    def __str__(self):
        return self.title
    @property
    def is_open(self):
        if self.is_active == self.ActiveOptions.ACTIVE:
            return True
        elif self.is_active == self.ActiveOptions.INACTIVE:
            return False
        now = timezone.now()
        return self.start_date <= now <= self.end_date

class ChallengeSubmission(models.Model):
    class GradeOptions(models.TextChoices):
        SIXTH   = '6', 'Grade 6'
        SEVENTH = '7', 'Grade 7'
        EIGHTH  = '8', 'Grade 8'
        NINTH   = '9', 'Grade 9'
        TENTH   = '10', 'Grade 10'

    challenge = models.ForeignKey(WeeklyChallenge, on_delete=models.CASCADE, related_name='submissions')
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    phone = models.CharField(max_length= 15)
    city = models.CharField(max_length=255)
    school = models.CharField(max_length=255)
    grade = models.CharField(max_length=2, choices=GradeOptions.choices)
    answer_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission by {self.firstname} {self.lastname} for {self.challenge.title}"