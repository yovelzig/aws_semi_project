import logging
import boto3

from config import Config, require_env


logger = logging.getLogger(__name__)

AWS_REGION = Config.AWS_REGION

AGENT_ID = require_env("BEDROCK_AGENT_ID")
AGENT_ALIAS_ID = require_env("BEDROCK_AGENT_ALIAS_ID")


bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=AWS_REGION
)


# def build_agent_input(question: str, session_id: str, history=None) -> str:
#     """
#     Builds the text sent to the AWS Bedrock Agent.

#     Project architecture:
#     - Flask calls the AWS Bedrock Agent.
#     - Tools are NOT implemented as internal Flask logic.
#     - Every tool must be executed through:
#       Bedrock Agent -> Action Group Function -> AWS Lambda.
#     - Each tool can have its own Lambda.
#     - Analytics Lambdas may call the secured Flask internal API to write/read
#       the existing SQLite database used by the project.
#     """

#     history = history or []

#     lines = []

#     for message in history[-6:]:
#         role = message.get("role", "")
#         content = (message.get("content") or "").strip()

#         if not content:
#             continue

#         if role == "user":
#             lines.append(f"User: {content}")
#         elif role == "assistant":
#             lines.append(f"Assistant: {content}")

#     conversation_context = "\n".join(lines) if lines else "No previous conversation."

#     return f"""
# You are handling a new current user request.

# Conversation history is provided only for context.
# Do not let old assistant answers replace the current instruction.
# Do not answer old questions unless the current user question clearly refers to them.

# Session ID:
# {session_id}

# Conversation history:
# {conversation_context}

# Current user question:
# {question}

# Main task:
# First search the connected Knowledge Base.
# Answer using the retrieved Knowledge Base content.

# Tool architecture rule:
# All tool actions must be executed only through AWS Bedrock Agent Action Group functions.
# Do not implement tools yourself.
# Do not call Flask directly yourself.
# Do not pretend to run tools.

# The Action Group functions are implemented by separate AWS Lambda functions.
# The Lambda functions may store or read analytics by calling the secured internal Flask analytics API.
# Flask is allowed to display dashboards and expose secured internal APIs, but Flask is not the tool executor.

# Available tool functions:
# - contactIT
# - logSupportInteraction
# - generateSupportAnalytics
# - detectKnowledgeGap

# Important:
# Do not say something was logged, saved, emailed, escalated, or analyzed unless the relevant Action Group function returned success.

# Critical grounding rules:
# 1. Use the retrieved Knowledge Base content as the source of truth.
# 2. Use conversation history only to understand references like "it", "that", or "the same issue".
# 3. Do not invent tools, commands, facts, escalation rules, categories, priorities, or procedures.
# 4. If the Knowledge Base does not contain enough information, call detectKnowledgeGap and then logSupportInteraction.

# Analytics request rule:
# If the user asks for analytics, dashboard data, support statistics, saved IT time, top categories, escalation rate, self-service rate, or knowledge gaps:
# - Call generateSupportAnalytics.
# - Use days from the user question.
# - If no number of days is provided, use days = "7".
# - Return the analytics result to the user.

# Mandatory escalation decision rule:
# You must decide escalation based on the CURRENT user question and the retrieved issue rules.

# Do NOT call contactIT only because the retrieved document contains:
# ACTION_REQUIRED: CONTACT_IT

# Call contactIT ONLY when:
# 1. The retrieved Knowledge Base issue contains Notify IT / Escalation rules, AND
# 2. The CURRENT user question clearly matches one or more conditions under "Notify IT When",
#    OR the retrieved issue is marked "Self-Service Level: No",
#    OR the user reports one of the following active problems:
#    - account lockout
#    - MFA lockout
#    - login blocked
#    - suspicious activity
#    - security issue
#    - production outage
#    - database issue
#    - SSL/certificate issue
#    - payment/order issue
#    - customer-facing system affected
#    - many users affected
#    - business-critical access blocked

# Do NOT call contactIT when:
# - The user only asks a general "how to" question.
# - The issue can be solved with Employee Self-Service Steps.
# - The user did not report a real active problem.
# - The user asks for information, explanation, learning, or prevention only.

# Support interaction logging rule:
# For every real support question, call logSupportInteraction before the final answer.

# Use these resolution types:
# - SELF_SERVICE: safe steps were provided and IT escalation is not required.
# - ESCALATED_TO_IT: contactIT was called successfully or escalation is required.
# - DIAGNOSTICS_REQUIRED: user needs to collect safe logs/screenshots/diagnostic info before final resolution.
# - UNKNOWN: not enough information or unclear category.

# Rules for logSupportInteraction:
# - sessionId = {session_id}
# - userQuestion = current user question
# - assistantAnswer = short final answer or short summary of the action taken
# - category = best matching category from the Knowledge Base
# - resolutionType = SELF_SERVICE, ESCALATED_TO_IT, DIAGNOSTICS_REQUIRED, or UNKNOWN
# - escalatedToIT = "true" or "false"
# - toolUsed = "none", "contactIT", "detectKnowledgeGap", "generateSupportAnalytics", "contactIT_failed", or combined tools
# - estimatedMinutesSaved:
#   - SELF_SERVICE: "10", "15", or "20" depending on complexity
#   - ESCALATED_TO_IT: "0"
#   - DIAGNOSTICS_REQUIRED: "5"
#   - UNKNOWN: "0"
# - employeeEmail = extract from current user question if present, otherwise "unknown"

# Escalation workflow:
# If escalation is required:
# 1. Call contactIT.
# 2. If contactIT returns success, call logSupportInteraction with:
#    - resolutionType = ESCALATED_TO_IT
#    - escalatedToIT = "true"
#    - toolUsed = "contactIT"
#    - estimatedMinutesSaved = "0"
# 3. Final user answer must be:
#    The issue was escalated to IT automatically.

# If contactIT fails:
# 1. Call logSupportInteraction with:
#    - resolutionType = ESCALATED_TO_IT
#    - escalatedToIT = "true"
#    - toolUsed = "contactIT_failed"
#    - estimatedMinutesSaved = "0"
# 2. Tell the user that escalation was required but automatic notification failed.

# Self-service workflow:
# If escalation is NOT required and the Knowledge Base provides safe steps:
# 1. Prepare the answer using Employee Self-Service Steps.
# 2. Call logSupportInteraction with:
#    - resolutionType = SELF_SERVICE
#    - escalatedToIT = "false"
#    - toolUsed = "none"
#    - estimatedMinutesSaved = "10", "15", or "20"
# 3. Return the self-service answer to the user.
# 4. Do not include ACTION_REQUIRED: CONTACT_IT in the user-facing answer.
# 5. Do not say that IT was contacted.

# Diagnostics workflow:
# If the user needs to collect safe logs, screenshots, command output, or environment details:
# 1. Provide only safe diagnostic collection steps.
# 2. Call logSupportInteraction with:
#    - resolutionType = DIAGNOSTICS_REQUIRED
#    - escalatedToIT = "false"
#    - toolUsed = "none"
#    - estimatedMinutesSaved = "5"
# 3. Return the diagnostic collection steps to the user.

# Knowledge gap workflow:
# If there is no good answer, the Knowledge Base does not contain enough information, or the user repeats an unresolved issue:
# 1. Call detectKnowledgeGap with:
#    - question = current user question
#    - category = best matching category or "Unknown"
#    - reason = short reason why the Knowledge Base is missing or weak
#    - suggestedArticleTitle = suggested title for a future Knowledge Base article if possible
# 2. Call logSupportInteraction with:
#    - resolutionType = UNKNOWN
#    - escalatedToIT = "false"
#    - toolUsed = "detectKnowledgeGap"
#    - estimatedMinutesSaved = "0"
# 3. Tell the user that the uploaded documents do not contain enough information.

# Safety:
# - Do not suggest dangerous actions.
# - Do not tell employees to change production, cloud, database, security, DNS, firewall, Kubernetes, Docker volume, or server settings unless the retrieved document explicitly says it is safe self-service.
# - Admin commands are for IT/Admin Notes only.
# - Do not expose ACTION_REQUIRED: CONTACT_IT to the user.
# """.strip()
def build_agent_input(question: str, session_id: str, history=None) -> str:
    history = history or []

    lines = []

    for message in history[-6:]:
        role = message.get("role", "")
        content = (message.get("content") or "").strip()

        if not content:
            continue

        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")

    conversation_context = "\n".join(lines) if lines else "No previous conversation."

    return f"""
You are handling a new current user request.

Session ID:
{session_id}

Conversation history:
{conversation_context}

Current user question:
{question}

Use the configured AWS Bedrock Agent instructions, Knowledge Base, and available Action Group tools.
Conversation history is only for context.
Focus on the current user question.
""".strip()


def ask_agent(question: str, session_id: str, history=None) -> str:
    input_text = build_agent_input(
        question=question,
        session_id=session_id,
        history=history
    )

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=True
        )

        logger.info("Agent raw response keys: %s", list(response.keys()))

        answer_chunks = []

        for event in response.get("completion", []):
            logger.info("Agent event: %s", event)

            chunk = event.get("chunk")

            if not chunk:
                continue

            bytes_data = chunk.get("bytes")

            if bytes_data:
                decoded = bytes_data.decode("utf-8")
                logger.info("Agent chunk text: %s", decoded)
                answer_chunks.append(decoded)

        answer = "".join(answer_chunks).strip()

        logger.info("Final agent answer: %s", answer)

        if not answer:
            return "I did not receive an answer from the AWS Bedrock Agent."

        return answer

    except Exception as e:
        logger.exception("Failed to invoke AWS Bedrock Agent")
        raise RuntimeError(f"Failed to invoke AWS Bedrock Agent: {e}")