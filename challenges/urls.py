from django.urls import path
from .views import ChallengeSubmissionView, ChallengeDetailView, LatestChallengeView, ChallengeListView

urlpatterns = [
    path('', ChallengeListView.as_view(), name='challenge-list'),
    path('latest/', LatestChallengeView.as_view(), name='latest-challenge'),
    path('<slug:slug>/', ChallengeDetailView.as_view(), name='challenge-detail'),
    path('<slug:slug>/submit/', ChallengeSubmissionView.as_view(), name='challenge-submit')
]