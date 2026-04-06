from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import WeeklyChallenge, ChallengeSubmission
from .serializers import Challengeserializer, ChallengeSubmissionSerializer


class ChallengeSubmissionView(APIView):
    def post(self, request, slug):
        try:
            challenge = WeeklyChallenge.objects.get(slug=slug)

            if (not challenge.is_open):
                return Response({"error": "این چالش فعال نیست"}, status=status.HTTP_403_FORBIDDEN)

            serializer = ChallengeSubmissionSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save(challenge=challenge)
                return Response({"message": "Saved Successfully!"}, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except WeeklyChallenge.DoesNotExist:
            return Response({"error": "Challenge not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChallengeDetailView(generics.RetrieveAPIView):
    queryset = WeeklyChallenge.objects.all()
    serializer_class = Challengeserializer
    lookup_field = 'slug'


class LatestChallengeView(APIView):
    def get(self, request):
        try:
            now = timezone.now()

            challenge = WeeklyChallenge.objects.active().order_by('-start_date').first()
            if not challenge:
                return Response({"error": "چالش فعالی وجود ندارد"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"slug": challenge.slug, "title": challenge.title, "description": challenge.description,
                             "regex": challenge.validation_regex})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


