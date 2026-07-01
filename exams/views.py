from django.conf import settings
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from rest_framework import viewsets, views, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

import core.settings
from .serializers import ExamListSerializer, ExamDetailSerializer, QuestionSerializer
from .models import ExamModel, QuestionModel, Submission
from .permissions import CanDesigne, CanViewQuestion, CanViewSubmission


class ExamsViewSet(viewsets.ModelViewSet):
    lookup_field = "id"
    permission_classes = [CanDesigne]

    def get_serializer_class(self):
        if self.action == 'list':
            return ExamListSerializer
        return ExamDetailSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.has_perm("exams.add_exammodl"):
            return ExamModel.objects.all()
        return ExamModel.objects.filter(is_visible=True)


    @extend_schema(
        summary="List exams",
        description="Return a list of all exams. Only visible exams are shown to users without permissions.",
        responses=ExamListSerializer(many=True)
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve exam details",
        description="Return detailed information of an exam including its questions.",
        responses=ExamDetailSerializer
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new exam",
        description="Create a new exam. Only users with design permissions can perform this action.",
        request=ExamDetailSerializer,
        responses={201: ExamDetailSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update an exam",
        description="Update an existing exam. Nested questions can also be updated.",
        request=ExamDetailSerializer,
        responses=ExamDetailSerializer
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete an exam",
        description="Delete an exam and all related questions.",
        responses={204: OpenApiResponse(description="Exam deleted successfully")}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)



class QuestionViewSet(viewsets.ModelViewSet):
    queryset = QuestionModel.objects.all()
    serializer_class = QuestionSerializer
    lookup_field = "id"
    permission_classes = [CanDesigne]

    @extend_schema(
        summary="List questions",
        description="Return all questions.",
        responses=QuestionSerializer(many=True)
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a question",
        description="Return details of a specific question.",
        responses=QuestionSerializer
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a question",
        description="Create a new question and associate it with an exam.",
        request=QuestionSerializer,
        responses={201: QuestionSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update a question",
        description="Update an existing question.",
        request=QuestionSerializer,
        responses=QuestionSerializer
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a question",
        description="Delete a specific question.",
        responses={204: OpenApiResponse(description="Question deleted successfully")}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class QuestionImageView(views.APIView):
    permission_classes = [CanViewQuestion]

    def get(self, request, pk):
        question: QuestionModel = get_object_or_404(QuestionModel, pk=pk)

        if not question.question_picture :
            raise NotFound("No Image")

        if core.settings.DEBUG :
            return FileResponse(question.question_picture.open())


        # TODO: test this later
        response = HttpResponse()
        response["X-Accel-Redirect"] = f"{question.question_picture}"
        return response


class SubmissionFileView(views.APIView):
    """
    Return a presigned URL (S3/MinIO) or serve the file directly (dev)
    for a given submission.
    """

    permission_classes = [CanViewSubmission]

    @extend_schema(
        summary="Get submission file URL",
        description=(
            "Returns a temporary presigned URL to download the submission file. "
            "In development mode, serves the file directly."
        ),
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Submission ID",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Presigned URL or file stream",
            ),
            403: OpenApiResponse(description="Not allowed to view this submission"),
            404: OpenApiResponse(description="Submission not found or has no file"),
        },
    )
    def get(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk)
        self.check_object_permissions(request, submission)

        if not submission.file:
            raise NotFound("This submission has no file attached.")

        storage = submission.file.storage
        try:
            url = storage.url(
                submission.file.name,
                expire=settings.S3_PRESIGNED_EXPIRE,
            )
        except TypeError:
            # FileSystemStorage.url() doesn't accept expire
            url = storage.url(submission.file.name)

        # Make the url absolute if it is relative (For dev only)
        if not url.startswith(("http://", "https://")):
            url = request.build_absolute_uri(url)

        return Response({"url": url}, status=status.HTTP_200_OK)