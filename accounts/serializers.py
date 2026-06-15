from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import OtpRequest, Province, City, School, User, DashboardResource
from .otp_service import OtpVerificationError, verify_otp
from .utils import normalize_phone, validate_national_code, validate_phone


class DashboardResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardResource
        fields = [
            "title",
            "description",
            "url",
            "type",
            "thumbnail",
            "category",
            "is_new",
        ]


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ["id", "title"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "title"]


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "title"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(write_only=True, min_length=6, max_length=6)

    class Meta:
        model = User
        fields = [
            "national_code",
            "phone",
            "birth_date",
            "Academic_Year",
            "school",
            "password",
            "otp_code",
        ]

    def validate_national_code(self, value):
        if not validate_national_code(value):
            raise serializers.ValidationError("کد ملی نامعتبر است")
        return value

    def validate_phone(self, value):
        value = normalize_phone(value)
        if not validate_phone(value):
            raise serializers.ValidationError("شماره موبایل نامعتبر است")
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("این شماره موبایل قبلا ثبت شده است")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        try:
            attrs["otp_request"] = verify_otp(
                phone=attrs["phone"],
                purpose=OtpRequest.Purpose.REGISTRATION,
                code=attrs["otp_code"],
            )
        except OtpVerificationError as exc:
            raise serializers.ValidationError({"otp_code": str(exc)}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("otp_code")
        otp_request = validated_data.pop("otp_request")
        validated_data["username"] = validated_data["national_code"]
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        otp_request.consume()
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    city = CitySerializer(source="school.city", read_only=True)
    province = ProvinceSerializer(source="school.city.province", read_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "national_code",
            "school",
            "city",
            "province",
            "phone",
        ]
        readonly_fields = fields


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class AuthLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AccessTokenSerializer(serializers.Serializer):
    access = serializers.CharField()


class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    purpose = serializers.ChoiceField(choices=OtpRequest.Purpose.choices)

    def validate_phone(self, value):
        value = normalize_phone(value)
        if not validate_phone(value):
            raise serializers.ValidationError("شماره موبایل نامعتبر است")
        return value

    def validate(self, attrs):
        phone = attrs["phone"]
        purpose = attrs["purpose"]
        user_exists = User.objects.filter(phone=phone).exists()
        if purpose == OtpRequest.Purpose.REGISTRATION and user_exists:
            raise serializers.ValidationError(
                {"phone": "این شماره موبایل قبلا ثبت شده است"}
            )
        if purpose == OtpRequest.Purpose.PASSWORD_RESET and not user_exists:
            raise serializers.ValidationError(
                {"phone": "کاربری با این شماره موبایل یافت نشد"}
            )
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)

    def validate_phone(self, value):
        value = normalize_phone(value)
        if not validate_phone(value):
            raise serializers.ValidationError("شماره موبایل نامعتبر است")
        if not User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("کاربری با این شماره موبایل یافت نشد")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11)
    otp_code = serializers.CharField(write_only=True, min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate_phone(self, value):
        value = normalize_phone(value)
        if not validate_phone(value):
            raise serializers.ValidationError("شماره موبایل نامعتبر است")
        return value

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        try:
            user = User.objects.get(phone=attrs["phone"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"phone": "کاربری با این شماره موبایل یافت نشد"}
            ) from exc

        try:
            attrs["otp_request"] = verify_otp(
                phone=attrs["phone"],
                purpose=OtpRequest.Purpose.PASSWORD_RESET,
                code=attrs["otp_code"],
            )
        except OtpVerificationError as exc:
            raise serializers.ValidationError({"otp_code": str(exc)}) from exc

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        self.validated_data["otp_request"].consume()
        return user
