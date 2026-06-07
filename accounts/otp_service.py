from __future__ import annotations

import json
import secrets
from datetime import timedelta
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import OtpRequest


class KavenegarSendError(Exception):
    """Raised when Kavenegar returns non-200 or HTTP fails."""


class OtpVerificationError(Exception):
    """Raised when an OTP cannot be verified."""


def _post(endpoint: str, data: dict) -> dict:
    api_key = settings.KAVENEGAR_API_KEY
    if not api_key:
        raise KavenegarSendError("KAVENEGAR_API_KEY is not configured")

    url = f"https://api.kavenegar.com/v1/{api_key}/{endpoint}.json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "charset": "utf-8",
    }
    timeout = int(getattr(settings, "KAVENEGAR_TIMEOUT_SECONDS", 10))
    encoded_data = urlencode(data).encode("utf-8")
    request = Request(url, data=encoded_data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as resp:
            response_text = resp.read().decode("utf-8")
    except HTTPError as exc:
        response_text = exc.read().decode("utf-8")
    except URLError as exc:
        raise KavenegarSendError(str(exc)) from exc

    try:
        body = json.loads(response_text)
    except ValueError as exc:
        raise KavenegarSendError("Invalid JSON from Kavenegar") from exc

    ret = body.get("return") or {}
    status = ret.get("status")
    if status == 200:
        return body
    message = ret.get("message", response_text)
    raise KavenegarSendError(f"Kavenegar error {status}: {message}")


def send_otp_code(
    *, receptor: str, token: str, type: Literal["sms", "call"] = "sms"
) -> None:
    template = settings.KAVENEGAR_OTP_TEMPLATE_NAME
    if not template:
        raise KavenegarSendError("KAVENEGAR_OTP_TEMPLATE_NAME is not configured")

    _post(
        "verify/lookup",
        {
            "receptor": receptor,
            "type": type,
            "template": template,
            "token": token,
        },
    )


def generate_otp_code() -> str:
    digits = int(getattr(settings, "OTP_CODE_DIGITS", 6))
    start = 10 ** (digits - 1)
    end = 10**digits
    return str(secrets.randbelow(end - start) + start)


def latest_active_otp(*, phone: str, purpose: str) -> OtpRequest | None:
    return (
        OtpRequest.objects.filter(
            phone=phone,
            purpose=purpose,
            consumed_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )


def create_and_send_otp(*, phone: str, purpose: str) -> OtpRequest:
    now = timezone.now()
    current = latest_active_otp(phone=phone, purpose=purpose)
    if current and current.resend_available_at > now:
        raise OtpVerificationError("لطفا کمی بعد دوباره تلاش کنید.")

    code = generate_otp_code()
    otp = OtpRequest.objects.create(
        phone=phone,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        resend_available_at=now
        + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS),
    )
    try:
        send_otp_code(receptor=phone, token=code)
    except KavenegarSendError:
        otp.delete()
        raise
    return otp


def verify_otp(*, phone: str, purpose: str, code: str) -> OtpRequest:
    otp = latest_active_otp(phone=phone, purpose=purpose)
    max_attempts = settings.OTP_MAX_VERIFY_ATTEMPTS
    if not otp or otp.is_expired or otp.attempts >= max_attempts:
        raise OtpVerificationError("کد تایید نامعتبر یا منقضی شده است.")

    if not check_password(code, otp.code_hash):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise OtpVerificationError("کد تایید نامعتبر یا منقضی شده است.")

    return otp
