from rest_framework.serializers import ModelSerializer, HyperlinkedModelSerializer, HyperlinkedIdentityField, SerializerMethodField
from .models import ExamModel, QuestionModel, Submission
from django.urls import reverse

class QuestionSerializer(ModelSerializer):
    question_picture = SerializerMethodField()
    class Meta:
        model=QuestionModel
        fields="__all__"

    def get_question_picture(self, obj: QuestionModel):
        request = self.context.get("request")

        if not obj.question_picture:
            return None
        url = reverse("question-image-view", kwargs={"pk": obj.id})
        if request:
            return request.build_absolute_uri(url)
        return url
        

class ExamListSerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(view_name="exams-detail", lookup_field="id")
    class Meta:
        model=ExamModel
        fields=["id","name","start_time", "url"]

class ExamDetailSerializer(ModelSerializer):
    questions=QuestionSerializer(many=True, read_only=True)

    class Meta:
        model=ExamModel
        fields="__all__"


class SubmissionSerializer(ModelSerializer):
    exam_id = SerializerMethodField()
    question_name = SerializerMethodField()
    max_grade = SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "user",
            "question",
            "question_name",
            "exam_id",
            "file",
            "grade",
            "max_grade",
            "uploaded_at",
        ]
        read_only_fields = ["id", "uploaded_at"]



    def get_exam_id(self, obj):
        return obj.question.exam_id

    def get_question_name(self, obj):
        return obj.question.sign_name

    def get_max_grade(self, obj):
        return obj.question.max_grade
