from rest_framework.serializers import ModelSerializer, HyperlinkedModelSerializer, HyperlinkedIdentityField
from .models import ExamModel, QuestionModel

class QuestionSerializer(ModelSerializer):
    class Meta:
        model=QuestionModel
        fields="__all__"
        

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

