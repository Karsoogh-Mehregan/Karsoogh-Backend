from rest_framework.serializers import ModelSerializer, HyperlinkedModelSerializer, HyperlinkedIdentityField, SerializerMethodField, ReadOnlyField
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
    exam_id = ReadOnlyField(source='question.exam_id')
    question_name = ReadOnlyField(source='question.sign_name')
    max_grade = ReadOnlyField(source='question.max_grade')

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
            "description",
            "max_grade",
        ]
        read_only_fields = [
            "id",
            "user",
            "question",
            "question_name",
            "file",
            "max_grade"
        ]

