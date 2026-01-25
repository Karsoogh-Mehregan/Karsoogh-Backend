from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AuthViewSet, ProvinceViewSet, CityViewSet, SchoolViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'provinces', ProvinceViewSet, basename='provinces')
router.register(r'cities', CityViewSet, basename='cities')
router.register(r'schools', SchoolViewSet, basename='schools')

urlpatterns = router.urls
