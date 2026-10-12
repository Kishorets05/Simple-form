
import os
import uuid

import boto3
from werkzeug.utils import secure_filename


# --------------------------------------------------
# AMAZON S3 CONFIGURATION
# --------------------------------------------------

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
)


# --------------------------------------------------
# UPLOAD FOLDER (LEGACY COMPATIBILITY)
# --------------------------------------------------

# Files are uploaded directly to S3.
# This variable is retained because app.py imports it.

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "uploads",
)


# --------------------------------------------------
# SAVE FILE TO AMAZON S3
# --------------------------------------------------

def save_file(request, field_name):
    """
    Upload a file directly to Amazon S3.

    Returns:
        S3 object key if a file was uploaded.
        None if no file was provided.
    """

    uploaded_file = request.files.get(field_name)

    if not uploaded_file or not uploaded_file.filename:
        return None

    if not S3_BUCKET_NAME:
        raise RuntimeError(
            "S3_BUCKET_NAME environment variable is missing."
        )

    original_filename = secure_filename(
        uploaded_file.filename
    )

    if not original_filename:
        return None

    # Generate a unique filename to avoid collisions.
    extension = os.path.splitext(
        original_filename
    )[1].lower()

    filename = (
        f"{uuid.uuid4().hex}_{field_name}{extension}"
    )

    content_type = (
        uploaded_file.mimetype
        or "application/octet-stream"
    )

    # Upload the file directly to the private S3 bucket.
    s3_client.upload_fileobj(
        uploaded_file,
        S3_BUCKET_NAME,
        filename,
        ExtraArgs={
            "ContentType": content_type,
        },
    )

    # Save this key in the MySQL database.
    return filename
