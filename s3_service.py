import boto3

from config import Config, require_env


s3 = boto3.client(
    "s3",
    region_name=Config.AWS_REGION
)

BUCKET_NAME = require_env("S3_BUCKET_NAME")


def upload_file_to_s3(file_path, s3_key):
    s3.upload_file(
        file_path,
        BUCKET_NAME,
        s3_key
    )

    return f"s3://{BUCKET_NAME}/{s3_key}"