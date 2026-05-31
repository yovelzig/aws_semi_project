# import boto3

# bedrock_runtime = boto3.client(
#     "bedrock-agent-runtime",
#     region_name="us-east-2"
# )

# KNOWLEDGE_BASE_ID = "ORD1CPDCWR"
# MODEL_ARN = "arn:aws:bedrock:us-east-2:881490130721:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"
# # arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0
# def ask_question(question):

#     response = bedrock_runtime.retrieve_and_generate(
#         input={
#             "text": question
#         },
#         retrieveAndGenerateConfiguration={
#             "type": "KNOWLEDGE_BASE",
#             "knowledgeBaseConfiguration": {
#                 "knowledgeBaseId": KNOWLEDGE_BASE_ID,
#                 "modelArn": MODEL_ARN
#             }
#         }
#     )

#     return response["output"]["text"]
import boto3


AWS_REGION = "us-east-2"

KNOWLEDGE_BASE_ID = "ORD1CPDCWR"

MODEL_ARN = (
    "arn:aws:bedrock:us-east-2:881490130721:"
    "inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"
)

def retrieve_debug(question):
    response = bedrock_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={
            "text": question
        },
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 10
            }
        }
    )

    results = response.get("retrievalResults", [])

    return [
        {
            "score": item.get("score"),
            "text": item.get("content", {}).get("text", ""),
            "location": item.get("location", {})
        }
        for item in results
    ]

bedrock_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=AWS_REGION
)


def build_conversation_context(history=None):
    """
    Converts previous chat messages into readable conversation context.

    Example:
    User: My Docker container keeps restarting
    Assistant: Check logs with docker logs...
    User: What should I check next?
    """

    if not history:
        return "No previous conversation."

    lines = []

    for message in history[-10:]:
        role = message.get("role", "")
        content = message.get("content", "")

        if not content:
            continue

        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")

    if not lines:
        return "No previous conversation."

    return "\n".join(lines)


def build_retrieval_query(question, history=None):
    """
    Builds a better query for the Knowledge Base.

    Why?
    If the user asks:
    1. "My Docker container keeps restarting"
    2. "What should I check first?"

    The second question alone is unclear.
    So we combine recent user messages with the current question.
    """

    if not history:
        return question

    recent_user_messages = [
        message.get("content", "")
        for message in history[-6:]
        if message.get("role") == "user" and message.get("content")
    ]

    combined_query = "\n".join(recent_user_messages + [question]).strip()

    return combined_query or question


def build_grounded_prompt(question, history=None):
    conversation_context = build_conversation_context(history)

    return f"""
You are a technical support AI assistant.

You must answer using ONLY information retrieved from the user's uploaded documents in the Knowledge Base.

Important rules:
1. Use the conversation history only to understand follow-up questions.
2. Do not use general knowledge unless it is supported by the retrieved documents.
3. If the uploaded documents do not contain enough information, say:
   "I do not have enough information in the uploaded documents to answer this."
4. Do not invent commands, facts, tools, steps, versions, or configuration values.
5. If the user asks a follow-up like "what about that?", "explain more", or "what should I do next?",
   use the previous conversation to understand what "that" means.

Conversation history:
{conversation_context}

Current user question:
{question}

Answer clearly as a technical support assistant.
Use this structure when possible:
- Short diagnosis
- Steps to check
- Suggested fix
- When to escalate
"""


def ask_question(question, history=None):
    history = history or []

    retrieval_query = build_retrieval_query(question, history)
    conversation_context = build_conversation_context(history)

    prompt_template = f"""
You are a technical support AI assistant.

You must answer using ONLY the retrieved search results from the uploaded documents.

Important rules:
- Do not use outside knowledge.
- Do not guess.
- If the retrieved search results do not contain the answer, say:
  "I do not have enough information in the uploaded documents to answer this."
- Use the conversation history only to understand follow-up questions, not as a factual source.
- If the retrieved search results directly answer the question, give the answer clearly and shortly.

Conversation history:
{conversation_context}

Retrieved search results:
$search_results$

Current user question:
{question}

Answer:
"""

    response = bedrock_runtime.retrieve_and_generate(
        input={
            "text": retrieval_query
        },
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                "modelArn": MODEL_ARN,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 10
                    }
                },
                "generationConfiguration": {
                    "promptTemplate": {
                        "textPromptTemplate": prompt_template
                    }
                }
            }
        }
    )

    return response["output"]["text"]