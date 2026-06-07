from submissions.exceptions import InvalidFileError
from core import settings

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


# TODO: WTF?
def validate_file(content_type: str, size: int):
    if content_type not in ALLOWED_TYPES:
        raise InvalidFileError("این فرمت فایل مجاز نیست!")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if size > max_bytes :
        raise InvalidFileError(f"حداکثر حجم مجاز برای ارسال  { settings.MAX_UPLOAD_SIZE_MB}MB است.")

