import smtplib
from email.message import EmailMessage
from config import Config


def send_email_to_it(
    user_question: str,
    assistant_answer: str,
    session_id: str
) -> dict:
    """
    Sends an automatic escalation email to the IT team.
    This tool is triggered when the RAG answer contains:
    ACTION_REQUIRED: CONTACT_IT
    """

    if not Config.ENABLE_IT_EMAIL_TOOL:
        return {
            "success": False,
            "status": "disabled",
            "message": "IT email tool is disabled."
        }

    required_values = {
        "SMTP_HOST": Config.SMTP_HOST,
        "SMTP_USERNAME": Config.SMTP_USERNAME,
        "SMTP_PASSWORD": Config.SMTP_PASSWORD,
        "SMTP_FROM_EMAIL": Config.SMTP_FROM_EMAIL,
        "IT_SUPPORT_EMAIL": Config.IT_SUPPORT_EMAIL,
    }

    missing = [key for key, value in required_values.items() if not value]

    if missing:
        return {
            "success": False,
            "status": "missing_config",
            "message": f"Missing email configuration: {', '.join(missing)}"
        }

    subject = f"IT Support Request - Session {session_id}"

    body = f"""
Hello IT team,

The AI support assistant detected that this issue requires IT involvement.

Session ID:
{session_id}

User Question:
{user_question}

Assistant Answer:
{assistant_answer}

Required Action:
Please review and contact the employee if needed.

Trigger:
ACTION_REQUIRED: CONTACT_IT
"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM_EMAIL
    msg["To"] = Config.IT_SUPPORT_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.send_message(msg)

        return {
            "success": True,
            "status": "sent",
            "message": "IT escalation email sent successfully."
        }

    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": str(e)
        }