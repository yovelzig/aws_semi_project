import boto3

from config import Config, require_env


bedrock_agent = boto3.client(
    "bedrock-agent",
    region_name=Config.AWS_REGION
)

KNOWLEDGE_BASE_ID = require_env("BEDROCK_KNOWLEDGE_BASE_ID")
DATA_SOURCE_ID = require_env("BEDROCK_DATA_SOURCE_ID")


def trigger_kb_sync():
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=DATA_SOURCE_ID
    )

    return response