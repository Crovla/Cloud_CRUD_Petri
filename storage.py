"""File storage. Local folder for development, S3-compatible bucket in the cloud.
Switch by setting S3_BUCKET (+ AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
AWS_DEFAULT_REGION and, for non-AWS providers, S3_ENDPOINT)."""
import os

BUCKET = os.environ.get("S3_BUCKET")
FOLDER = "uploads"

if BUCKET:
    import boto3
    s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT"))
else:
    os.makedirs(FOLDER, exist_ok=True)


def save(key, data, content_type):
    if BUCKET:
        s3.put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)
    else:
        with open(os.path.join(FOLDER, key), "wb") as f:
            f.write(data)


def load(key):
    try:
        if BUCKET:
            return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        with open(os.path.join(FOLDER, os.path.basename(key)), "rb") as f:
            return f.read()
    except Exception:
        return None


def delete(key):
    try:
        if BUCKET:
            s3.delete_object(Bucket=BUCKET, Key=key)
        else:
            os.remove(os.path.join(FOLDER, os.path.basename(key)))
    except Exception:
        pass
