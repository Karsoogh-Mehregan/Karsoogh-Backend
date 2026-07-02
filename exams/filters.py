import django_filters
from .models import Submission


class SubmissionFilter(django_filters.FilterSet):
    # Filter by submission ID
    id = django_filters.NumberFilter()
    id__gte = django_filters.NumberFilter(field_name="id", lookup_expr="gte")
    id__lte = django_filters.NumberFilter(field_name="id", lookup_expr="lte")

    # Filter by question
    question = django_filters.NumberFilter(field_name="question__id")
    question_name = django_filters.CharFilter(field_name="question__sign_name", lookup_expr="icontains")

    # Filter by exam
    exam = django_filters.NumberFilter(field_name="question__exam__id")
    exam_name = django_filters.CharFilter(field_name="question__exam__name", lookup_expr="icontains")

    # Filter by user
    user = django_filters.NumberFilter(field_name="user__id")
    username = django_filters.CharFilter(field_name="user__username", lookup_expr="icontains")

    # Filter by grade
    grade = django_filters.NumberFilter()
    grade__gte = django_filters.NumberFilter(field_name="grade", lookup_expr="gte")
    grade__lte = django_filters.NumberFilter(field_name="grade", lookup_expr="lte")
    graded = django_filters.BooleanFilter(field_name="grade", lookup_expr="isnull", exclude=True)

    # Filter by upload date
    uploaded_after = django_filters.DateTimeFilter(field_name="uploaded_at", lookup_expr="gte")
    uploaded_before = django_filters.DateTimeFilter(field_name="uploaded_at", lookup_expr="lte")

    class Meta:
        model = Submission
        fields = [
            "id", "question", "exam", "user", "grade", "graded",
        ]
