from django.conf import settings
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiParameter
from rest_framework import viewsets, views, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .serializers import ExamListSerializer, ExamDetailSerializer, QuestionSerializer, SubmissionSerializer
from .models import ExamModel, QuestionModel, Submission
from .permissions import CanDesigne, CanViewQuestion, CanViewSubmission, CanGradeSubmission
from .filters import SubmissionFilter


@extend_schema_view(
    list=extend_schema(
        summary="List exams",
        description="Return a list of all exams. Only visible exams are shown to users without permissions.",
        responses=ExamListSerializer(many=True)
    ),
    retrieve=extend_schema(
        summary="Retrieve exam details",
        description="Return detailed information of an exam including its questions.",
        responses=ExamDetailSerializer
    ),
    create=extend_schema(
        summary="Create a new exam",
        description="Create a new exam. Only users with design permissions can perform this action.",
        request=ExamDetailSerializer,
        responses={201: ExamDetailSerializer}
    ),
    update=extend_schema(
        summary="Update an exam",
        description="Update an existing exam. Nested questions can also be updated.",
        request=ExamDetailSerializer,
        responses=ExamDetailSerializer
    ),
    destroy=extend_schema(
        summary="Delete an exam",
        description="Delete an exam and all related questions.",
        responses={204: OpenApiResponse(description="Exam deleted successfully")}
    ),
)
class ExamsViewSet(viewsets.ModelViewSet):
    lookup_field = "id"
    permission_classes = [CanDesigne]

    def get_serializer_class(self):
        if self.action == 'list':
            return ExamListSerializer
        return ExamDetailSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.has_perm("exams.add_exammodel"):
            return ExamModel.objects.all()
        return ExamModel.objects.filter(is_visible=True)



@extend_schema_view(
    list=extend_schema(
        summary="List questions",
        description="Return all questions.",
        responses=QuestionSerializer(many=True)
    ),
    retrieve=extend_schema(
        summary="Retrieve a question",
        description="Return details of a specific question.",
        responses=QuestionSerializer
    ),
    create=extend_schema(
        summary="Create a question",
        description="Create a new question and associate it with an exam.",
        request=QuestionSerializer,
        responses={201: QuestionSerializer}
    ),
    update=extend_schema(
        summary="Update a question",
        description="Update an existing question.",
        request=QuestionSerializer,
        responses=QuestionSerializer
    ),
    destroy=extend_schema(
        summary="Delete a question",
        description="Delete a specific question.",
        responses={204: OpenApiResponse(description="Question deleted successfully")}
    ),
)
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = QuestionModel.objects.all()
    serializer_class = QuestionSerializer
    lookup_field = "id"
    permission_classes = [CanDesigne]


class QuestionImageView(views.APIView):
    permission_classes = [CanViewQuestion]

    def get(self, request, pk):
        question: QuestionModel = get_object_or_404(QuestionModel, pk=pk)

        if not question.question_picture:
            raise NotFound("No Image")

        if settings.DEBUG:
            return FileResponse(question.question_picture.open())

        # Production: use the storage backend to get the URL
        # (returns a presigned URL for S3, or a relative path for local storage)
        url = question.question_picture.url
        return HttpResponseRedirect(url)


class SubmissionDetailView(views.APIView):
    """
    Get the details of a submission (including its file URL and grade)
    or set/update its grade.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [CanGradeSubmission()]
        return [CanViewSubmission()]

    @extend_schema(
        summary="Get submission details",
        description="Returns the details of the submission including the grade and the absolute file download URL.",
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Submission ID",
            ),
        ],
        responses={
            200: SubmissionSerializer,
            403: OpenApiResponse(description="Not allowed to view this submission"),
            404: OpenApiResponse(description="Submission not found"),
        },
    )
    def get(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk)
        self.check_object_permissions(request, submission)

        serializer = SubmissionSerializer(submission, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Set/Update submission grade",
        description="Assigns or updates the grade of the submission. Only staff/superusers or users with change_submission permission can perform this action.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "grade": {"type": "integer", "description": "The grade to assign"}
                },
                "required": ["grade"]
            }
        },
        responses={
            200: SubmissionSerializer,
            400: OpenApiResponse(description="Invalid grade value or missing field"),
            403: OpenApiResponse(description="Not allowed to grade this submission"),
            404: OpenApiResponse(description="Submission not found"),
        },
    )
    def post(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk)
        self.check_object_permissions(request, submission)

        grade_value = request.data.get("grade")
        if grade_value is None:
            return Response({"error": "Grade field is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            grade_value = int(grade_value)
        except (ValueError, TypeError):
            return Response({"error": "Grade must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate against max_grade
        max_grade = submission.question.max_grade
        if grade_value < 0 or (max_grade is not None and grade_value > max_grade):
            return Response(
                {"error": f"Grade must be between 0 and {max_grade}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        submission.grade = grade_value
        submission.save(update_fields=["grade"])

        serializer = SubmissionSerializer(submission, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubmissionListView(ListAPIView):
    """
    Paginated list of all submissions.
    Only staff/superusers can access the full list.
    Regular users only see their own submissions.
    Supports filtering by id, question, exam, user, grade, graded status, and upload date.
    Supports ordering by id, uploaded_at, grade.
    """
    serializer_class = SubmissionSerializer
    permission_classes = [CanViewSubmission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = SubmissionFilter
    ordering_fields = ["id", "uploaded_at", "grade"]
    ordering = ["-uploaded_at"]

    def get_queryset(self):
        qs = Submission.objects.select_related(
            "user", "question", "question__exam"
        )
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

