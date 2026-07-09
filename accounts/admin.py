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
    list_display = ("username", "first_name", "last_name", "national_code", "phone", "Academic_Year", "school", "is_staff")
    search_fields = ("username", "national_code", "phone", "first_name", "last_name")
    list_filter = ("Academic_Year", "school", "is_staff", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Informations", {"fields": ("national_code", "phone", "birth_date", "Academic_Year", "school")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Informations", {"fields": ("national_code", "phone", "birth_date", "Academic_Year", "school")}),
    )
    actions = ["set_as_staff"]

    @admin.action(description="Set selected users as staff")
    def set_as_staff(self, request, queryset):
        queryset.update(is_staff=True)



@admin.register(DashboardResource)
class DashboardResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "category", "is_new", "order", "created_at")
    list_filter = ("type", "category", "is_new")
    search_fields = ("title", "description", "url", "category")
    list_editable = ("order", "is_new")
    ordering = ("order", "-created_at")