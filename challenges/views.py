from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from .models import WeeklyChallenge, ChallengeSubmission
from .serializers import Challengeserializer, ChallengeSubmissionSerializer


class ChallengeSubmissionView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, slug):
        try:
            challenge = WeeklyChallenge.objects.get(slug=slug)

            if not challenge.is_public and not request.user.is_authenticated:
                return Response({"error": "برای شرکت در این چالش باید وارد حساب کاربری خود شوید"}, status=status.HTTP_401_UNAUTHORIZED)

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
    permission_classes = [AllowAny]
    serializer_class = Challengeserializer
    lookup_field = 'slug'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return WeeklyChallenge.objects.all()
        return WeeklyChallenge.objects.filter(is_public=True)


class ChallengeListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = Challengeserializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return WeeklyChallenge.objects.all().order_by('-start_date')
        return WeeklyChallenge.objects.filter(is_public=True).order_by('-start_date')


class LatestChallengeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:

            queryset = WeeklyChallenge.objects.active()
            if not request.user.is_authenticated:
                queryset = queryset.filter(is_public=True)

            challenge = queryset.order_by('-start_date').first()
            if not challenge:
                return Response({"error": "چالش فعالی وجود ندارد"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"slug": challenge.slug, "title": challenge.title, "description": challenge.description,
                             "regex": challenge.validation_regex})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


