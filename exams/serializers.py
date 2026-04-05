from rest_framework.serializers import ModelSerializer, HyperlinkedModelSerializer, HyperlinkedIdentityField, SerializerMethodField
from .models import ExamModel, QuestionModel
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

