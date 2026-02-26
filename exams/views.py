from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ExamListSerializer, ExamDetailSerializer, QuestionSerializer
from .models import ExamModel, QuestionModel
from .permissions import CanDesigne

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