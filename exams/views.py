from django.utils import timezone
from django.conf import settings
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample, OpenApiParameter
from rest_framework import viewsets, views, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .serializers import ExamListSerializer, ExamDetailSerializer, QuestionSerializer, SubmissionSerializer
from .models import ExamModel, QuestionModel, Submission
from .permissions import CanDesigne, CanViewQuestion, CanViewSubmission, CanGradeSubmission, IsAdminUser
from .filters import SubmissionFilter
from accounts.models import User


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
        responses={
            200: SubmissionSerializer,
            403: OpenApiResponse(description="Not allowed to view this submission"),
            404: OpenApiResponse(description="Submission not found"),
        },
        examples=[
            OpenApiExample(
                "Successful response",
                value={
                    "id": 1,
                    "user": 1,
                    "question": 1,
                    "question_name": "Question 1",
                    "exam_id": 1,
                    "file": "http://example.com/media/submissions/1/1/solution.pdf",
                    "grade": 85,
                    "max_grade": 100,
                },
                response_only=True,
            ),
        ],
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
                    "grade": {"type": "integer", "description": "The grade to assign"},
                    "description": {"type": "string", "description": "Optional description or feedback from the grader"}
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
        examples=[
            OpenApiExample(
                "Successful grading",
                value={
                    "id": 1,
                    "user": 1,
                    "question": 1,
                    "question_name": "Question 1",
                    "exam_id": 1,
                    "file": "http://example.com/media/submissions/1/1/solution.pdf",
                    "grade": 90,
                    "max_grade": 100,
                },
                response_only=True,
            ),
            OpenApiExample(
                "Invalid grade",
                value={"error": "Grade must be between 0 and 100."},
                response_only=True,
            ),
            OpenApiExample(
                "Valid grade request",
                value={"grade": 85, "description": "wrong calculation in part 2"},
                request_only=True,
            ),
            OpenApiExample(
                "Invalid grade request (out of range)",
                value={"grade": 150},
                request_only=True,
            ),
        ],
    )
    def patch(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk)
        self.check_object_permissions(request, submission)

        grade_value = request.data.get("grade")
        description = request.data.get("description", "")

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
        submission.description = description
        submission.graded_by = request.user
        submission.graded_at = timezone.now()
        submission.save(update_fields=["grade", "description", "graded_by", "graded_at"])

        serializer = SubmissionSerializer(submission, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
        summary="List submissions",
        description="Returns a paginated list of submissions. Staff/superusers see all submissions, regular users only see their own.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by submission ID",
            ),
            OpenApiParameter(
                name="id__gte",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by submission ID greater than or equal to",
            ),
            OpenApiParameter(
                name="id__lte",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by submission ID less than or equal to",
            ),
            OpenApiParameter(
                name="question",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by question ID",
            ),
            OpenApiParameter(
                name="question_name",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by question name (case-insensitive partial match)",
            ),
            OpenApiParameter(
                name="exam",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by exam ID",
            ),
            OpenApiParameter(
                name="exam_name",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by exam name (case-insensitive partial match)",
            ),
            OpenApiParameter(
                name="user",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by user ID",
            ),
            OpenApiParameter(
                name="username",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by username (case-insensitive partial match)",
            ),
            OpenApiParameter(
                name="grade",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by grade",
            ),
            OpenApiParameter(
                name="grade__gte",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by grade greater than or equal to",
            ),
            OpenApiParameter(
                name="grade__lte",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by grade less than or equal to",
            ),
            OpenApiParameter(
                name="graded",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by whether submission has been graded (true) or not graded (false)",
            ),
            OpenApiParameter(
                name="uploaded_after",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by upload date after (ISO 8601 format)",
            ),
            OpenApiParameter(
                name="uploaded_before",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by upload date before (ISO 8601 format)",
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Order results by id, uploaded_at, or grade (prefix with '-' for descending)",
            ),
        ],
        responses={
            200: SubmissionSerializer(many=True),
            403: OpenApiResponse(description="Not allowed to view submissions"),
        },
        
    )
class SubmissionListView(ListAPIView):
    """
    Paginated list of submissions.
    Superusers and staff with view permission can see all submissions.
    Staff only see submissions assigned to them as grader.
    Students cannot access submissions.
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
        user = self.request.user
        qs = Submission.objects.select_related(
            "user", "question", "question__exam"
        )
        
        # Superusers can see all
        if user.is_superuser or (user.is_staff and user.has_perm("exams.view_submission")):
            return qs
            
        # Staff only see submissions assigned to them as grader
        if user.is_staff:
            return qs.filter(graders=user).distinct()

        # Regular users (students) cannot access the submissions list
        return qs.none()

class AssignGraderView(views.APIView):
    permission_classes = [IsAdminUser]
    @extend_schema(
        summary="Assign a grader to a submission",
        description="Assigns a specific user as the grader for a given submission. Only accessible by superusers.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "grader_id": {"type": "integer", "description": "The ID of the user to assign as the grader"}
                },
                "required": ["grader_id"]
            }
        },
        responses={
            200: OpenApiResponse(
                description="Grader assigned successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"message": "Grader user_name assigned successfully."},
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(description="Missing grader_id or invalid data"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Submission or User not found"),
        },
        examples=[
            OpenApiExample(
                "Successful assignment",
                value={"grader_id": 5},
                request_only=True,
            ),
        ],
    )
    def post(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk)
        grader_id = request.data.get("grader_id")
        
        grader = get_object_or_404(User, pk=grader_id)
        
        submission.grader = grader
        submission.save()
        return Response({"message": f"Grader {grader.username} assigned successfully."})
    