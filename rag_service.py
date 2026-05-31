import boto3

bedrock_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name="us-east-2"
)

KNOWLEDGE_BASE_ID = "ORD1CPDCWR"
MODEL_ARN = "arn:aws:bedrock:us-east-2:881490130721:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"
# arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0
def ask_question(question):

    response = bedrock_runtime.retrieve_and_generate(
        input={
            "text": question
        },
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                "modelArn": MODEL_ARN
            }
        }
    )

    return response["output"]["text"]