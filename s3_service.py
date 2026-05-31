import boto3


s3 = boto3.client("s3")

BUCKET_NAME = "oz-private-user9"  # Replace with your bucket name


def upload_file_to_s3(file_path, s3_key):
    s3.upload_file(
        file_path,
        BUCKET_NAME,
        s3_key
    )

    return f"s3://{BUCKET_NAME}/{s3_key}"