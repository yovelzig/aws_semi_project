import boto3

bedrock_agent = boto3.client(
    "bedrock-agent",
    region_name="us-east-2"
)

KNOWLEDGE_BASE_ID = "ORD1CPDCWR"
DATA_SOURCE_ID = "GSHI7R3JO7"


def trigger_kb_sync():
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=DATA_SOURCE_ID
    )

    return response