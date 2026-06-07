import boto3
from botocore.exceptions import ClientError

from core import settings
from submissions.exceptions import StorageError

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY
)

def generate_presigned_upload_url(key: str, content_type: str) -> str:
    try:
        return s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.S3_PRESIGNED_EXPIRE
        )
    except ClientError as e:
        raise StorageError(f"Failed to generate upload URL: {str(e)}")


def generate_presigned_download_url(key: str, expires=3600) -> str:
    try:
        return s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=expires,
        )
    except ClientError as e:
        raise StorageError(f"Failed to generate download URL: {str(e)}")


def file_exists(key: str) -> bool:
    try:
        s3_client.head_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key
        )
        return True
    except ClientError:
        return False

def delete_file(key: str):
    try:
        s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key
        )
    except ClientError as e:
        raise StorageError(f"Delete Failed: {str(e)}")