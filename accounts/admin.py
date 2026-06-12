from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import City, OtpRequest, Province, School, User, DashboardResource

# Register your models here.
admin.site.register(Province)
admin.site.register(City)
admin.site.register(School)
admin.site.register(OtpRequest)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    pass


@admin.register(DashboardResource)
class DashboardResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "category", "is_new", "order", "created_at")
    list_filter = ("type", "category", "is_new")
    search_fields = ("title", "description", "url", "category")
    list_editable = ("order", "is_new")
    ordering = ("order", "-created_at")