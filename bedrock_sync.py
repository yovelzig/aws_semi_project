import boto3

from config import Config, require_env


bedrock_agent = boto3.client(
    "bedrock-agent",
    region_name=Config.AWS_REGION
)

KNOWLEDGE_BASE_ID = require_env("BEDROCK_KNOWLEDGE_BASE_ID")
DATA_SOURCE_ID = require_env("BEDROCK_DATA_SOURCE_ID")


def trigger_kb_sync():
    """
    Starts ingestion job for the Knowledge Base Data Source.

    This is still required even when the app asks questions through an Agent,
    because the uploaded S3 file must be indexed into the Knowledge Base.
    """

    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=DATA_SOURCE_ID
    )

    ingestion_job = response.get("ingestionJob", {})

    return {
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "data_source_id": DATA_SOURCE_ID,
        "ingestion_job_id": ingestion_job.get("ingestionJobId"),
        "status": ingestion_job.get("status"),
        "raw": response
    }