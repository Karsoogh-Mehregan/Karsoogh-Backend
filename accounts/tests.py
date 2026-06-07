from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import OtpRequest
from .otp_service import KavenegarSendError

User = get_user_model()


@override_settings(
    OTP_EXPIRY_MINUTES=5,
    OTP_RESEND_COOLDOWN_SECONDS=60,
    OTP_MAX_VERIFY_ATTEMPTS=5,
    KAVENEGAR_API_KEY="test-key",
    KAVENEGAR_OTP_TEMPLATE_NAME="test-template",
)
class OtpAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_payload = {
            "national_code": "0084575948",
            "phone": "09123456789",
            "birth_date": "2010-01-01",
            "Academic_Year": 7,
            "password": "StrongPass123!",
            "otp_code": "123456",
        }

    def test_registration_otp_request_creates_otp(self):
        with (
            patch("accounts.otp_service.generate_otp_code", return_value="123456"),
            patch("accounts.otp_service.send_otp_code") as send_otp_code,
        ):
            response = self.client.post(
                "/auth/users/request-otp/",
                {"phone": "09123456789", "purpose": "registration"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(OtpRequest.objects.count(), 1)
        send_otp_code.assert_called_once_with(
            receptor="09123456789",
            token="123456",
        )

    def test_registration_rejects_duplicate_phone(self):
        User.objects.create_user(
            username="1234567891",
            national_code="1234567891",
            phone="09123456789",
            password="StrongPass123!",
        )

        response = self.client.post(
            "/auth/users/request-otp/",
            {"phone": "09123456789", "purpose": "registration"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_registration_creates_user_after_valid_otp(self):
        self._create_otp(
            phone="09123456789",
            purpose=OtpRequest.Purpose.REGISTRATION,
        )

        response = self.client.post(
            "/auth/users/register/",
            self.register_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(phone="09123456789")
        self.assertEqual(user.username, "0084575948")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertIsNotNone(OtpRequest.objects.get(phone="09123456789").consumed_at)

    def test_registration_rejects_invalid_phone_national_code_and_otp(self):
        payload = {
            **self.register_payload,
            "phone": "123",
            "national_code": "0012345678",
            "otp_code": "000000",
        }

        response = self.client.post(
            "/auth/users/register/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_registration_rejects_expired_otp(self):
        self._create_otp(
            phone="09123456789",
            purpose=OtpRequest.Purpose.REGISTRATION,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            "/auth/users/register/",
            self.register_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_forgot_password_request_requires_existing_phone(self):
        response = self.client.post(
            "/auth/forgot-password/",
            {"phone": "09123456789"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        User.objects.create_user(
            username="0084575948",
            national_code="0084575948",
            phone="09123456789",
            password="OldStrongPass123!",
        )
        with (
            patch("accounts.otp_service.generate_otp_code", return_value="123456"),
            patch("accounts.otp_service.send_otp_code"),
        ):
            response = self.client.post(
                "/auth/forgot-password/",
                {"phone": "09123456789"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            OtpRequest.objects.filter(
                phone="09123456789",
                purpose=OtpRequest.Purpose.PASSWORD_RESET,
            ).exists()
        )

    def test_reset_password_with_valid_otp(self):
        User.objects.create_user(
            username="0084575948",
            national_code="0084575948",
            phone="09123456789",
            password="OldStrongPass123!",
        )
        self._create_otp(
            phone="09123456789",
            purpose=OtpRequest.Purpose.PASSWORD_RESET,
        )

        response = self.client.post(
            "/auth/reset-password/",
            {
                "phone": "09123456789",
                "otp_code": "123456",
                "new_password": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(
            authenticate(username="0084575948", password="NewStrongPass123!")
        )

    def test_reset_password_rejects_wrong_reused_and_over_attempted_otp(self):
        User.objects.create_user(
            username="0084575948",
            national_code="0084575948",
            phone="09123456789",
            password="OldStrongPass123!",
        )
        otp = self._create_otp(
            phone="09123456789",
            purpose=OtpRequest.Purpose.PASSWORD_RESET,
        )

        response = self.client.post(
            "/auth/reset-password/",
            {
                "phone": "09123456789",
                "otp_code": "000000",
                "new_password": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        otp.attempts = 5
        otp.save(update_fields=["attempts"])
        response = self.client.post(
            "/auth/reset-password/",
            {
                "phone": "09123456789",
                "otp_code": "123456",
                "new_password": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        otp.attempts = 0
        otp.consumed_at = timezone.now()
        otp.save(update_fields=["attempts", "consumed_at"])
        response = self.client.post(
            "/auth/reset-password/",
            {
                "phone": "09123456789",
                "otp_code": "123456",
                "new_password": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_kavenegar_failure_returns_bad_gateway(self):
        with patch(
            "accounts.views.create_and_send_otp",
            side_effect=KavenegarSendError("boom"),
        ):
            response = self.client.post(
                "/auth/users/request-otp/",
                {"phone": "09123456789", "purpose": "registration"},
                format="json",
            )

        self.assertEqual(response.status_code, 502)
        self.assertFalse(OtpRequest.objects.exists())

    def _create_otp(self, *, phone, purpose, expires_at=None):
        now = timezone.now()
        return OtpRequest.objects.create(
            phone=phone,
            purpose=purpose,
            code_hash=make_password("123456"),
            expires_at=expires_at or now + timedelta(minutes=5),
            resend_available_at=now,
        )
