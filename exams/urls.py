from rest_framework.routers import DefaultRouter
from .views import ExamsViewSet, QuestionViewSet
router=DefaultRouter()

router.register(r"exams",ExamsViewSet,basename='exams')
router.register(r"questions", QuestionViewSet, basename="questions")
urlpatterns = router.urls

