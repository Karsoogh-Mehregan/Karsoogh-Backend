import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import WeeklyChallenge, ChallengeSubmission


def export_submissions(modeladmin, request, queryset):

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="submissions.csv"'

    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)

    writer.writerow(['Challenge', 'First Name', 'Last Name', 'Phone', 'City', 'School', 'Grade', 'Answer Text', 'Submitted At'])

    for submission in queryset:
        writer.writerow([
            submission.challenge.title,
            submission.firstname,
            submission.lastname,
            submission.phone,
            submission.city,
            submission.school,
            submission.grade,
            submission.answer_text,
            submission.submitted_at
        ])

    return response
export_submissions.short_description = "Export Selected Submissions to CSV"


@admin.register(WeeklyChallenge)
class WeeklyChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(ChallengeSubmission)
class ChallengeSubmissionAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'firstname', 'lastname', 'phone', 'city', 'school', 'grade', 'submitted_at')
    list_filter = ('submitted_at', 'challenge', 'grade')
    search_fields = ('firstname', 'lastname', 'phone', 'answer_text', 'city', 'school', 'grade')
    actions = [export_submissions]
