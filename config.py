import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

    BEDROCK_KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
    BEDROCK_DATA_SOURCE_ID = os.getenv("BEDROCK_DATA_SOURCE_ID")
    BEDROCK_MODEL_ARN = os.getenv("BEDROCK_MODEL_ARN")


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value