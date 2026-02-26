from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter
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
        description="Log in with national code and password to obtain JWT tokens.",
        request=AuthLoginSerializer,
        responses={
            200: TokenPairSerializer,
            400: MessageSerializer,
            401: MessageSerializer,
        },
    )
    @action(detail=False,methods=['post'])
    def login(self, request):
        national_code = request.data.get('national_code')
        password = request.data.get('password')

        if not national_code or not password:
            return Response(
                {"message": "کد ملی و رمز عبور الزامی است"},
                status=status.HTTP_400_BAD_REQUEST
                )


        user = authenticate(
            request,
            username=national_code,
            password=password
        )

        if user is None:
            return Response(
                {"message" : "کد ملی یا رمز عبور اشتباه است!"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })
        
    @extend_schema(
        description="Refresh JWT access token using a refresh token.",
        request=TokenRefreshSerializer,
        responses={200: AccessTokenSerializer, 400: MessageSerializer},
    )
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        try:
            refresh = RefreshToken(request.data.get('refresh'))
            return Response({
                "access": str(refresh.access_token)
            })
        except Exception:
            return Response(
                {'message': 'توکن نامعتبر است.'},
                status=status.HTTP_400_BAD_REQUEST
                )
        