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


def build_agent_input(question: str, history=None) -> str:
    """
    Builds the text sent to the AWS Bedrock Agent.

    History is preserved, but the current user request and escalation rule
    are made explicit so previous assistant answers do not override tool usage.
    """

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

Conversation history is provided only for context.
Do not let old assistant answers replace the current instruction.

Conversation history:
{conversation_context}

Current user question:
{question}

Mandatory escalation rule:
First search the connected Knowledge Base.

You must decide escalation based on the CURRENT user question, not only because
the retrieved document contains the text ACTION_REQUIRED: CONTACT_IT.

Call the contactIT function from the ITSupportActions action group ONLY when:
1. The retrieved Knowledge Base issue contains Notify IT / Escalation rules, AND
2. The CURRENT user question clearly matches one or more conditions under "Notify IT When",
   or the issue is marked "Self-Service Level: No",
   or the user reports account lockout, MFA lockout, login blocked, security issue,
   production outage, database issue, SSL/certificate issue, payment/order issue,
   many users affected, business-critical access problem, or suspicious activity.

Do NOT call contactIT when:
- The user only asks a general "how to" question.
- The issue can be solved with Employee Self-Service Steps.
- The user did not report a real active problem.
- The retrieved document contains ACTION_REQUIRED: CONTACT_IT but the current question
  does not match an escalation condition.

If escalation is required:
- You MUST call contactIT.
- Do not only tell the user to contact IT.
- Do not only provide an IT notification template.
- Do not ask the user for permission before calling contactIT.

When calling contactIT:
- userQuestion = the current user question
- assistantAnswer = short explanation of why IT intervention is required
- issueCategory = best matching category from the retrieved issue
- priority = high for account lockout, MFA lockout, login blocked, security,
  production, many users, database, SSL, payments, orders, customer-facing systems,
  or business-critical access problems. Otherwise medium.
- employeeEmail = extract an email from the current user question if present, otherwise unknown

After contactIT succeeds, answer the user:
The issue was escalated to IT automatically.

If escalation is NOT required:
Answer with the Employee Self-Service Steps only.
Do not include ACTION_REQUIRED: CONTACT_IT in the user-facing answer.


def ask_agent(question: str, session_id: str, history=None) -> str:
    
    input_text = build_agent_input(
        question=question,
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