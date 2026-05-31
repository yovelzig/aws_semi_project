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

from config import Config, require_env


AWS_REGION = Config.AWS_REGION

KNOWLEDGE_BASE_ID = require_env("BEDROCK_KNOWLEDGE_BASE_ID")

MODEL_ARN = require_env("BEDROCK_MODEL_ARN")

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
    Build a retrieval query for the Knowledge Base.

    Rules:
    - If the current question is standalone, retrieve only by the current question.
    - If the current question is a follow-up, use recent history only to clarify
      what the user is referring to.
    - Do not include multiple old questions because that causes unrelated retrieval.
    """

    if not history:
        return question

    follow_up_phrases = [
        "what about",
        "explain more",
        "tell me more",
        "what should i check next",
        "what next",
        "next",
        "that",
        "this",
        "it",
        "how about",
        "and now",
        "continue",
        "more details",
    ]

    normalized_question = question.lower().strip()

    is_follow_up = any(phrase in normalized_question for phrase in follow_up_phrases)

    if not is_follow_up:
        return question

    recent_user_messages = [
        message.get("content", "")
        for message in history[-6:]
        if message.get("role") == "user" and message.get("content")
    ]

    previous_topic = recent_user_messages[-1] if recent_user_messages else ""

    if not previous_topic:
        return question

    return f"""
Previous topic:
{previous_topic}

Follow-up question:
{question}
""".strip()

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
You are a knowledge base assistant.

Your job:
Answer the CURRENT user question using ONLY the retrieved search results
from the uploaded documents.

Critical rules:
1. The retrieved search results are the ONLY factual source.
2. The conversation history is for understanding references only.
   Examples: "it", "that", "this issue", "what next", "explain more".
3. The conversation history is NOT a source of factual information.
4. If the retrieved search results contain a direct answer to the current question,
   you MUST answer with that information.
5. Do NOT reject an answer just because it looks like test data, demo data,
   sports data, or something outside technical support.
6. Do NOT answer previous questions unless the current question explicitly asks about them.
7. Do NOT combine multiple old questions into one answer.
8. Do NOT use outside knowledge.
9. Do NOT guess.
10. If the retrieved search results do not contain enough information, say exactly:
    "I do not have enough information in the uploaded documents to answer this."

Conversation history, for reference only:
{conversation_context}

Retrieved search results:
$search_results$

Current user question:
{question}

Answer only the current user question.

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