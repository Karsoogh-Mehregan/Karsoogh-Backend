from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# Create your models here.
class Province(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]


class City(models.Model):
    title = models.CharField(max_length=255)
    province = models.ForeignKey(Province, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["province"]


class School(models.Model):
    title = models.CharField(max_length=255)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} ({self.city.title})"

    class Meta:
        ordering = ["city"]


class User(AbstractUser):
    Academic_Year_Choose = [
        (7, "هفتم"),
        (8, "هشتم"),
        (9, "نهم"),
    ]

    national_code = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=11, unique=True)
    birth_date = models.DateField(null=True, blank=True)
    Academic_Year = models.IntegerField(choices=Academic_Year_Choose, default=7)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    # Todo: fix this after exam
    email = models.EmailField(null=True)


class OtpRequest(models.Model):
    class Purpose(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        PASSWORD_RESET = "password_reset", "Password reset"

    phone = models.CharField(max_length=11, db_index=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    resend_available_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone", "purpose", "created_at"]),
        ]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None

    def consume(self):
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])
