import csv
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.html import format_html

from accounts.models import User
from .models import ExamModel, QuestionModel, Submission

admin.site.register(ExamModel)


@admin.register(QuestionModel)
class QuestionModelAdmin(admin.ModelAdmin):
    list_display = ("id", "sign_name", "exam", "max_grade")
    list_filter = ("exam",)
    search_fields = ("sign_name",)


def export_submissions(modeladmin, request, queryset: list[Submission]):

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="submissions.csv"'

    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)

    writer.writerow(['Question' ,'ID', 'Username', 'Province', 'City', 'School', 'Assigned Graders', 'Grade', 'Grader Description', 'Graded By', 'Graded At'])


    for submission in queryset:
        user = submission.user
        school = user.school
        city = school.city if school else None
        province = city.province if city else None

        writer.writerow([
            submission.question.sign_name,
            submission.pk,
            user.username,
            province if province else '',
            city if city else '',
            school if school else '',
            ', '.join([grader.get_full_name() or grader.username for grader in submission.graders.all()]),
            submission.grade,
            submission.grader_description,
            submission.graded_by.get_full_name() if submission.graded_by else '',
            submission.graded_at,
        ])

    return response
export_submissions.short_description = "Export Selected Submissions to CSV"


def assign_graders(modeladmin, request, queryset):
    if "apply_assign" in request.POST or "apply_remove" in request.POST:
        grader_ids = request.POST.getlist("graders")
        if grader_ids:
            graders = User.objects.filter(pk__in=grader_ids)
            if "apply_assign" in request.POST:
                for submission in queryset:
                    submission.graders.add(*graders)
                modeladmin.message_user(
                    request,
                    f"Assigned {len(graders)} grader(s) to {queryset.count()} submission(s).",
                    messages.SUCCESS,
                )
            elif "apply_remove" in request.POST:
                for submission in queryset:
                    submission.graders.remove(*graders)
                modeladmin.message_user(
                    request,
                    f"Removed {len(graders)} grader(s) from {queryset.count()} submission(s).",
                    messages.SUCCESS,
                )
        return None

    available_graders = User.objects.filter(is_staff=True, is_active=True).order_by("first_name", "last_name")
    context = {
        "submissions": queryset,
        "available_graders": available_graders,
        "ids": request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME),
        "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
    }
    return render(request, "admin/exams/assign_graders.html", context)


assign_graders.short_description = "Assign or remove graders from selected submissions"


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "city_and_school", "question", "grade", "get_graders", "uploaded_at")
    list_filter = ("question__exam", "question", "uploaded_at")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__national_code",
        "user__phone",
        "question__sign_name",
        "graders__username",
        "graders__first_name",
        "graders__last_name"
    )
    raw_id_fields = ("user", "question")
    list_editable = ("grade",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("graders")
    actions = [export_submissions, assign_graders]

    readonly_fields = ("uploaded_at", "graded_at", "graded_by")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("file", "user")
        return self.readonly_fields

    filter_horizontal = ("graders",)

    fieldsets = (
        ("Submission Information", {
            "fields": ("user", "question", "file", "uploaded_at"),
        }),
        ("Grading Details", {
            "fields": ("grade", "graded_by", "grader_description", "graded_at"),
        }),
        ("Assigned Graders", {
            "fields": ("graders",),
        }),
    )

    @admin.display(description="City / School", ordering="user__school__city__title")
    def city_and_school(self, obj):
        school = obj.user.school
        if school:
            city = school.city
            return f"{city.title} / {school.title}" if city else school.title
        return "-"

    @admin.display(description="Graders")
    def get_graders(self, obj):
        return ", ".join(grader.get_full_name() or grader.username for grader in obj.graders.all())
