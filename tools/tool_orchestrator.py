from database import save_escalation_event
from tools.it_email_tool import send_email_to_it


ESCALATION_TRIGGER = "ACTION_REQUIRED: CONTACT_IT"


def should_contact_it(answer: str) -> bool:
    if not answer:
        return False

    return ESCALATION_TRIGGER in answer


def run_tools_after_answer(
    session_id: str,
    user_question: str,
    assistant_answer: str
) -> dict:
    """
    Runs backend tools after the RAG answer is generated.

    Current behavior:
    - If answer contains ACTION_REQUIRED: CONTACT_IT
    - Send email to IT
    - Save escalation event to SQLite
    """

    tool_results = {
        "tools_called": [],
        "escalation_required": False
    }

    if should_contact_it(assistant_answer):
        tool_results["escalation_required"] = True

        result = send_email_to_it(
            user_question=user_question,
            assistant_answer=assistant_answer,
            session_id=session_id
        )

        tool_results["tools_called"].append({
            "tool_name": "send_email_to_it",
            "result": result
        })

        save_escalation_event(
            session_id=session_id,
            user_question=user_question,
            assistant_answer=assistant_answer,
            tool_name="send_email_to_it",
            status=result.get("status", "unknown"),
            details=result.get("message", "")
        )

    return tool_results