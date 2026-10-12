import mimetypes
import os
import uuid
import boto3
from werkzeug.utils import secure_filename


# --------------------------------------------------
# AMAZON S3 CONFIGURATION
# --------------------------------------------------

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "registration-form-files-2026")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")


def get_s3_client():
    """
    Initialize and return an Amazon S3 client using environment variables.
    """
    client_kwargs = {
        "region_name": AWS_REGION,
    }
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        client_kwargs["aws_access_key_id"] = access_key
        client_kwargs["aws_secret_access_key"] = secret_key

    return boto3.client("s3", **client_kwargs)


s3_client = get_s3_client()


# --------------------------------------------------
# UPLOAD FOLDER (LEGACY COMPATIBILITY)
# --------------------------------------------------

# Local upload folder path retained for backward compatibility.
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "uploads",
)


# --------------------------------------------------
# S3 FILE OPERATIONS
# --------------------------------------------------

def save_file(request, field_name):
    """
    Upload a file directly to Amazon S3.

    Args:
        request: Flask request object containing form files.
        field_name: The name of the file field (photo, audio, video, document).

    Returns:
        S3 object key string if a file was uploaded.
        None if no file was provided.
    """
    if field_name not in request.files:
        return None

    uploaded_file = request.files.get(field_name)

    if not uploaded_file or not uploaded_file.filename:
        return None

    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME environment variable is missing.")

    original_filename = secure_filename(uploaded_file.filename)

    if not original_filename:
        return None

    # Generate a unique S3 object key to avoid collisions
    extension = os.path.splitext(original_filename)[1].lower()
    unique_key = f"{uuid.uuid4().hex}_{field_name}{extension}"

    content_type = (
        uploaded_file.mimetype
        or mimetypes.guess_type(original_filename)[0]
        or "application/octet-stream"
    )

    try:
        s3_client.upload_fileobj(
            uploaded_file,
            S3_BUCKET_NAME,
            unique_key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )
        return unique_key
    except Exception as e:
        print(f"Error uploading {field_name} to Amazon S3: {e}")
        raise e


def generate_presigned_url(s3_key, expiration=3600, as_attachment=False):
    """
    Generate a temporary presigned URL for private Amazon S3 object access.

    Args:
        s3_key: S3 object key.
        expiration: Duration in seconds before the presigned URL expires (default 1 hour).
        as_attachment: If True, adds Content-Disposition header to force browser download.

    Returns:
        Presigned URL string, or None on failure.
    """
    if not s3_key:
        return None

    params = {
        "Bucket": S3_BUCKET_NAME,
        "Key": s3_key,
    }

    if as_attachment:
        download_filename = s3_key.split("_", 1)[-1] if "_" in s3_key else s3_key
        params["ResponseContentDisposition"] = f'attachment; filename="{download_filename}"'

    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiration,
        )
        return url
    except Exception as e:
        print(f"Error generating presigned URL for '{s3_key}': {e}")
        return None


def delete_file_from_s3(s3_key):
    """
    Safely delete a single object from Amazon S3.

    Args:
        s3_key: S3 object key to delete.

    Returns:
        True if deleted successfully, False otherwise.
    """
    if not s3_key:
        return False

    try:
        s3_client.delete_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
        )
        return True
    except Exception as e:
        print(f"Error deleting S3 object '{s3_key}': {e}")
        return False


def delete_files_from_s3(s3_keys):
    """
    Safely delete multiple objects from Amazon S3.

    Args:
        s3_keys: Iterable of S3 object keys.
    """
    if not s3_keys:
        return

    for key in s3_keys:
        if key:
            delete_file_from_s3(key)
