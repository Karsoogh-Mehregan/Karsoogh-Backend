from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ExamsViewSet, QuestionViewSet, QuestionImageView, SubmissionListView, SubmissionDetailView

router=DefaultRouter()

router.register(r"exams",ExamsViewSet,basename='exams')
router.register(r"questions", QuestionViewSet, basename="questions")
urlpatterns = router.urls


urlpatterns += [
    path('questions/<int:pk>/image', QuestionImageView.as_view(), name='question-image-view'),
    path('submissions/', SubmissionListView.as_view(), name='submission-list'),
    path('submissions/<int:pk>/', SubmissionDetailView.as_view(), name='submission-detail'),
]

