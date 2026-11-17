from rest_framework import serializers
from django.utils.html import strip_tags
from django.core.validators import RegexValidator

from .models import WeeklyChallenge, ChallengeSubmission
import re


class Challengeserializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()
    regex = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyChallenge
        fields = ['title', 'slug', 'description', 'is_open', 'start_date', 'end_date', 'regex']

    def get_is_open(self, obj):
        return obj.is_open

    def get_regex(self, obj):
        return obj.validation_regex


class ChallengeSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeSubmission
        fields = ['firstname', 'lastname', 'phone', 'school',
                  'postal_code', 'address', 'grade', 'answer_text', 'submitted_at']
        extra_kwargs = {
            'postal_code': {
                'required': True, 'allow_blank': False,
                'validators': [RegexValidator(r'^\d{10}$', 'کد پستی باید ۱۰ رقم باشد')],
            },
            'address': {'required': True, 'allow_blank': False},
        }

    def validate(self, data):
        text_fields = ['firstname', 'lastname', 'school', 'address', 'answer_text']
        for field in text_fields:
            if field in data:
                clean = strip_tags(data[field])
                if clean != data[field]:
                    data[field] = clean
        challenge = self.context.get('challenge')
        if challenge and challenge.validation_regex:
            pattern = challenge.validation_regex
            answer = data.get('answer_text', '')
            try:
                if not re.fullmatch(pattern, answer):
                    raise serializers.ValidationError({"answer_text": "پاسخ نامعتبر است."})
            except re.error:
                pass
        return data