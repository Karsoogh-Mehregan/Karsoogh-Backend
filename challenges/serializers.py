from rest_framework import serializers
from django.utils.html import strip_tags
from .models import WeeklyChallenge, ChallengeSubmission
import re


class Challengeserializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyChallenge
        fields = ['title', 'slug', 'description', 'is_open', 'start_date', 'end_date']

    def get_is_open(self, obj):
        return obj.is_open


class ChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = ['firstname', 'lastname', 'phone', 'city', 'school', 'grade', 'answer_text', 'submitted_at']

    def validate(self, data):
        text_fields = ['firstname', 'lastname', 'city', 'school', 'answer_text']

        for field in text_fields:
            if field in data:
                clean = strip_tags(data[field])
                if clean != data[field]:
                    data[field] = clean

        challenge = self.context.get('challenge')
        if challenge and challenge.validation_regex:
            pattern = challenge.validation_regex
            answer = data.get('answer_text', '')

            if not re.fullmatch(pattern, answer):
                raise serializers.ValidationError("Answer does not match the required format.")

        return data