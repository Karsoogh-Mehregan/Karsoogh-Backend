from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from core.settings import ACCESS_TOKEN_LIFETIME_MINUTES, REFRESH_TOKEN_LIFETIME_DAYS
from .models import Province, City, School
from .serializers import (
    UserCreateSerializer,
    UserDetailSerializer,
    ProvinceSerializer,
    CitySerializer,
    SchoolSerializer,
    MessageSerializer,
    AuthLoginSerializer,
    TokenPairSerializer,
    TokenRefreshSerializer,
    AccessTokenSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework.views import exception_handler
import json



class ProvinceViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        description="List all provinces.",
        responses=ProvinceSerializer(many=True),
    )
    def list(self, request):
        provinces = Province.objects.all()
        serializer = ProvinceSerializer(provinces, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        description="Create a new province (admin only).",
        request=ProvinceSerializer,
        responses={201: MessageSerializer, 400: MessageSerializer},
    )
    def create(self, request):
        if not request.user.is_staff:
            return Response({"message": "You are not allowed"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProvinceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "The province added."},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CityViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        description="List cities in a given province.",
        parameters=[
            OpenApiParameter(
                name="province_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the province",
            )
        ],
        responses=CitySerializer(many=True),
    )
    @action(detail=False, methods=['get'], url_path='(?P<province_id>[^/.]+)')
    def by_province(self, request, province_id=None):
        cities = City.objects.filter(province_id=province_id)
        serializer = CitySerializer(cities, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        description="Create a new city (admin only).",
        request=CitySerializer,
        responses={201: MessageSerializer, 400: MessageSerializer},
    )
    def create(self, request):
        if not request.user.is_staff:
            return Response({"message": "You are not allowed"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = CitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "The city added."},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class SchoolViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        description="List schools in a given city.",
        parameters=[
            OpenApiParameter(
                name="city_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the city",
            )
        ],
        responses=SchoolSerializer(many=True),
    )
    @action(detail=False, methods=['get'], url_path='(?P<city_id>[^/.]+)')
    def by_city(self, request, city_id=None):
        schools = School.objects.filter(city_id=city_id)
        serializer = SchoolSerializer(schools, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        description="Create a new school (admin only).",
        request=SchoolSerializer,
        responses={201: MessageSerializer, 400: MessageSerializer},
    )
    def create(self, request):
        if not request.user.is_staff:
            return Response({"message": "You are not allowed"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SchoolSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "The school added."},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

User = get_user_model()


class UserViewSet(viewsets.ViewSet):
    @extend_schema(
        description="Register a new user.",
        request=UserCreateSerializer,
        responses={201: MessageSerializer, 400: MessageSerializer},
    )
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "ثبت نام با موفقیت انجام شد."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        description="Retrieve the authenticated user's profile.",
        responses=UserDetailSerializer,
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


class AuthViewSet(viewsets.ViewSet):
    permission_classes=[AllowAny]

    @extend_schema(
        description="Log in with username and password to obtain JWT tokens.",
        request=AuthLoginSerializer,
        responses={
            200: MessageSerializer,
            400: MessageSerializer,
            401: MessageSerializer,
        },
    )
    @action(detail=False,methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"message": "کد ملی و رمز عبور الزامی است"},
                status=status.HTTP_400_BAD_REQUEST
                )


        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {"message" : "کد ملی یا رمز عبور اشتباه است!"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)

        response = Response({
            "message": "ورود با موفقیت انجام شد.",
            "user": UserDetailSerializer(user).data
        }, status=status.HTTP_200_OK)
        
        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            httponly=True,
            secure=True,
            samesite='Lax',
            max_age=ACCESS_TOKEN_LIFETIME_MINUTES*60,
            path="/"
        )

        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite='Lax',
            max_age=REFRESH_TOKEN_LIFETIME_DAYS*86400,
            path="/"
        )

        return response

    @extend_schema(
        description="Refresh JWT access token using a refresh token.",
        request=TokenRefreshSerializer,
        responses={200: MessageSerializer, 400: MessageSerializer},
    )
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {'message': 'توکن یافت نشد.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            response = Response(
                {
                    "message": "توکن تمدید شد."
                }, status=status.HTTP_200_OK
            )
            response.set_cookie(
                key='access_token',
                value=str(refresh.access_token),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=ACCESS_TOKEN_LIFETIME_MINUTES * 60,
                path="/"
            )
            return response


        except TokenError:
            return Response(
                {'message': 'توکن منقضی یا نامعتبر است.'},
                status=status.HTTP_401_UNAUTHORIZED
                )
        
        except Exception:
            return Response(
                {'message': 'خطای سرور.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        response = Response({'message': 'با موفقیت خارج شدید.'})
        response.delete_cookie('refresh_token')
        response.delete_cookie('access_token')
        return response