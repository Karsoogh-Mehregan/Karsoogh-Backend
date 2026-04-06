from rest_framework import serializers
from django.utils.html import strip_tags
from .models import WeeklyChallenge, ChallengeSubmission
import re


class Challengeserializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyChallenge
        fields = ['title', 'slug', 'description', 'is_active', 'created_at']


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