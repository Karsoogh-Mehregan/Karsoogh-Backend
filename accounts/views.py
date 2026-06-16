from rest_framework import generics
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from core.settings import ACCESS_TOKEN_LIFETIME_MINUTES, REFRESH_TOKEN_LIFETIME_DAYS
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Province, City, School, DashboardResource
from .otp_service import KavenegarSendError, OtpVerificationError, create_and_send_otp
from .serializers import (
    AuthLoginSerializer,
    CitySerializer,
    DashboardResourceSerializer,
    ForgotPasswordSerializer,
    MessageSerializer,
    OtpRequestSerializer,
    ProvinceSerializer,
    ResetPasswordSerializer,
    SchoolSerializer,
    TokenRefreshSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
)


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
            return Response(
                {"message": "You are not allowed"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProvinceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "The province added."}, status=status.HTTP_201_CREATED
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
    @action(detail=False, methods=["get"], url_path="(?P<province_id>[^/.]+)")
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
            return Response(
                {"message": "You are not allowed"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = CitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "The city added."}, status=status.HTTP_201_CREATED
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
    @action(detail=False, methods=["get"], url_path="(?P<city_id>[^/.]+)")
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
            return Response(
                {"message": "You are not allowed"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = SchoolSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "The school added."}, status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


User = get_user_model()


class UserViewSet(viewsets.ViewSet):
    @extend_schema(
        description="Request an OTP for registration or password reset.",
        request=OtpRequestSerializer,
        responses={
            200: MessageSerializer,
            400: MessageSerializer,
            502: MessageSerializer,
        },
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        url_path="request-otp",
    )
    def request_otp(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            create_and_send_otp(**serializer.validated_data)
        except OtpVerificationError as exc:
            return Response(
                {"message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except KavenegarSendError:
            return Response(
                {"message": "ارسال کد تایید با مشکل مواجه شد."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"message": "کد تایید ارسال شد."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description="Register a new user.",
        request=UserCreateSerializer,
        responses={201: MessageSerializer, 400: MessageSerializer},
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "ثبت نام با موفقیت انجام شد."},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Retrieve the authenticated user's profile.",
        responses=UserDetailSerializer,
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def profile(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        description="Log in with username and password to obtain JWT tokens.",
        request=AuthLoginSerializer,
        responses={
            200: MessageSerializer,
            400: MessageSerializer,
            401: MessageSerializer,
        },
    )
    @action(detail=False, methods=["post"])
    def login(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"message": "نام کاربری و رمز عبور الزامی است"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response(
                {"message": "نام کاربری یا رمز عبور اشتباه است!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "message": "ورود با موفقیت انجام شد.",
                "user": UserDetailSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=ACCESS_TOKEN_LIFETIME_MINUTES * 60,
            path="/",
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=REFRESH_TOKEN_LIFETIME_DAYS * 86400,
            path="/",
        )

        return response

    @extend_schema(
        description="Refresh JWT access token using a refresh token.",
        request=TokenRefreshSerializer,
        responses={200: MessageSerializer, 400: MessageSerializer},
    )
    @action(detail=False, methods=["post"])
    def refresh(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"message": "توکن یافت نشد."}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            response = Response(
                {"message": "توکن تمدید شد."}, status=status.HTTP_200_OK
            )
            response.set_cookie(
                key="access_token",
                value=str(refresh.access_token),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=ACCESS_TOKEN_LIFETIME_MINUTES * 60,
                path="/",
            )
            return response

        except TokenError:
            return Response(
                {"message": "توکن منقضی یا نامعتبر است."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except Exception:
            return Response(
                {"message": "خطای سرور."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        response = Response({"message": "با موفقیت خارج شدید."})
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        return response

    @extend_schema(
        description="Request password reset OTP by phone.",
        request=ForgotPasswordSerializer,
        responses={
            200: MessageSerializer,
            400: MessageSerializer,
            502: MessageSerializer,
        },
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        url_path="forgot-password",
    )
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            create_and_send_otp(
                phone=serializer.validated_data["phone"],
                purpose="password_reset",
            )
        except OtpVerificationError as exc:
            return Response(
                {"message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except KavenegarSendError:
            return Response(
                {"message": "ارسال کد تایید با مشکل مواجه شد."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"message": "کد تایید ارسال شد."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description="Reset password using phone and OTP.",
        request=ResetPasswordSerializer,
        responses={200: MessageSerializer, 400: MessageSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        url_path="reset-password",
    )
    def reset_password(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "رمز عبور با موفقیت تغییر کرد."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
        description="List all dashboard resources, optionally filtered by category.",
        parameters=[
            OpenApiParameter(
                name="category",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter resources by category name",
                required=False,
            )
        ],
        responses=DashboardResourceSerializer(many=True),
    )
class DashboardResourceViewSet(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DashboardResourceSerializer
    queryset = DashboardResource.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset

