from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class Province(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']


class City(models.Model):
    title = models.CharField(max_length=255)
    province = models.ForeignKey(Province, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['province']


class School(models.Model):
    title = models.CharField(max_length=255)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} ({self.city.title})"
    
    class Meta:
        ordering = ['city']


class User(AbstractUser):
    Academic_Year_Choose = [
        (7, 'هفتم'),
        (8, 'هشتم'),
        (9, 'نهم'),
    ]

    national_code = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=11)
    birth_date = models.DateField(null=True, blank=True)
    Academic_Year = models.IntegerField(choices=Academic_Year_Choose, default=7)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)

    USERNAME_FIELD = 'national_code'
    REQUIRED_FIELDS = ['username']