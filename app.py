import logging
import os
import uuid

from config import require_env, Config
from flask import Flask, render_template, request, jsonify, session

from database import (
    init_db,
    save_message,
    get_history,
    save_support_interaction,
    save_knowledge_gap,
)

from agent_service import ask_agent
from rag_service import retrieve_debug
from s3_service import upload_file_to_s3
from bedrock_sync import trigger_kb_sync

from analytics_dashboard_service import (
    build_summary,
    get_categories,
    get_interactions,
    get_dashboard_knowledge_gaps,
    get_dashboard_payload,
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = require_env("SECRET_KEY")

init_db()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

def require_internal_tool_key():
    expected_key = Config.INTERNAL_TOOL_API_KEY

    if not expected_key:
        return False

    received_key = request.headers.get("X-Internal-Tool-Key", "")

    return received_key == expected_key

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    return render_template("index.html")


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")


def is_last_question_request(question: str) -> bool:
    q = question.lower().strip()

    patterns = [
        "what was my last question",
        "what was the last question",
        "what did i ask last",
        "what did i just ask",
        "מה הייתה השאלה האחרונה שלי",
        "מה השאלה האחרונה שלי",
        "מה שאלתי קודם",
        "מה שאלתי לפני",
    ]

    return any(pattern in q for pattern in patterns)


def get_previous_user_question(history: list) -> str | None:
    """
    Returns the previous real user question from chat history.

    The current user question is not saved yet when this function runs,
    so the latest user message in history is the previous question.
    """

    for message in reversed(history):
        if message.get("role") == "user":
            content = (message.get("content") or "").strip()

            if not content:
                continue

            if is_last_question_request(content):
                continue

            return content

    return None


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}

    question = (data.get("message") or "").strip()
    frontend_session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "Empty question"}), 400

    session_id = frontend_session_id or session.get("session_id") or str(uuid.uuid4())
    session["session_id"] = session_id

    try:
        history = get_history(session_id, limit=10)

        if is_last_question_request(question):
            last_question = get_previous_user_question(history)

            if last_question:
                answer = f'Your last question was: "{last_question}"'
            else:
                answer = "I don't see a previous question in this chat."

            save_message(session_id, "user", question)
            save_message(session_id, "assistant", answer)

            return jsonify({
                "answer": answer,
                "session_id": session_id
            })

        llm_history = [
            {
                "role": h["role"],
                "content": h["content"]
            }
            for h in history
        ]

        answer = ask_agent(
            question=question,
            session_id=session_id,
            history=llm_history
        )

        save_message(session_id, "user", question)
        save_message(session_id, "assistant", answer)

        return jsonify({
            "answer": answer,
            "session_id": session_id
        })

    except Exception as e:
        logging.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/history")
def history():
    session_id = session.get("session_id")

    if not session_id:
        return jsonify([])

    return jsonify(get_history(session_id))


@app.route("/api/new_session", methods=["POST"])
def new_session():
    session["session_id"] = str(uuid.uuid4())

    return jsonify({
        "session_id": session["session_id"]
    })


@app.route("/api/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        local_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(local_path)

        s3_uri = upload_file_to_s3(
            local_path,
            f"data/{file.filename}"
        )

        sync_response = trigger_kb_sync()

        return jsonify({
            "success": True,
            "file": file.filename,
            "s3_uri": s3_uri,
            "message": "Uploaded to S3 and Knowledge Base sync started. The AWS Agent will use the updated Knowledge Base after ingestion completes.",
            "sync": sync_response
        })

    except Exception as e:
        logging.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/debug/retrieve", methods=["POST"])
def debug_retrieve():
    data = request.get_json() or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"error": "Empty question"}), 400

    results = retrieve_debug(question)

    return jsonify({
        "question": question,
        "results_count": len(results),
        "results": results
    })


@app.route("/api/analytics/summary")
def api_analytics_summary():
    days = int(request.args.get("days", "7"))

    return jsonify(build_summary(days=days))


@app.route("/api/analytics/categories")
def api_analytics_categories():
    days = int(request.args.get("days", "7"))

    return jsonify({
        "days": days,
        "categories": get_categories(days=days)
    })


@app.route("/api/analytics/interactions")
def api_analytics_interactions():
    days = int(request.args.get("days", "7"))
    limit = int(request.args.get("limit", "20"))

    return jsonify({
        "days": days,
        "interactions": get_interactions(days=days, limit=limit)
    })


@app.route("/api/analytics/knowledge-gaps")
def api_analytics_knowledge_gaps():
    limit = int(request.args.get("limit", "20"))

    return jsonify({
        "knowledgeGaps": get_dashboard_knowledge_gaps(limit=limit)
    })

@app.route("/api/analytics/dashboard")
def api_analytics_dashboard():
    days = int(request.args.get("days", "7"))

    return jsonify(get_dashboard_payload(days=days))

@app.route("/api/internal/tools/log-support-interaction", methods=["POST"])
def internal_log_support_interaction():
    if not require_internal_tool_key():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}

    interaction_id = data.get("interactionId") or str(uuid.uuid4())
    session_id = data.get("sessionId") or "unknown-session"
    user_question = data.get("userQuestion") or ""
    assistant_answer = data.get("assistantAnswer") or ""
    category = data.get("category") or "Unknown"
    resolution_type = data.get("resolutionType") or "UNKNOWN"
    escalated_to_it = str(data.get("escalatedToIT", "false")).lower()
    tool_used = data.get("toolUsed") or "none"
    employee_email = data.get("employeeEmail") or "unknown"

    try:
        estimated_minutes_saved = int(data.get("estimatedMinutesSaved", 0))
    except (TypeError, ValueError):
        estimated_minutes_saved = 0

    save_support_interaction(
        interaction_id=interaction_id,
        session_id=session_id,
        user_question=user_question,
        assistant_answer=assistant_answer,
        category=category,
        resolution_type=resolution_type,
        escalated_to_it=escalated_to_it,
        tool_used=tool_used,
        estimated_minutes_saved=estimated_minutes_saved,
        employee_email=employee_email,
    )

    return jsonify({
        "success": True,
        "message": "Support interaction logged successfully.",
        "interactionId": interaction_id
    })


@app.route("/api/internal/tools/detect-knowledge-gap", methods=["POST"])
def internal_detect_knowledge_gap():
    if not require_internal_tool_key():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}

    gap_id = data.get("gapId") or str(uuid.uuid4())
    question = data.get("question") or ""
    category = data.get("category") or "Unknown"
    reason = data.get("reason") or "Not enough information in Knowledge Base"
    suggested_article_title = data.get("suggestedArticleTitle") or ""

    save_knowledge_gap(
        gap_id=gap_id,
        question=question,
        category=category,
        reason=reason,
        suggested_article_title=suggested_article_title,
    )

    return jsonify({
        "success": True,
        "message": "Knowledge gap logged successfully.",
        "gapId": gap_id
    })


@app.route("/api/internal/tools/generate-support-analytics", methods=["GET"])
def internal_generate_support_analytics():
    if not require_internal_tool_key():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    days = int(request.args.get("days", "7"))

    summary = build_summary(days=days)
    categories = get_categories(days=days)
    interactions = get_interactions(days=days, limit=10)

    return jsonify({
        "success": True,
        "days": days,
        "summary": summary,
        "topCategories": categories[:10],
        # "latestInteractions": interactions
    })

if __name__ == "__main__":
    print("IT AI assistant ready at http://localhost:5000")
    print("Mode: AWS Bedrock Agent + S3 upload + Knowledge Base sync")
    app.run(debug=False, host="0.0.0.0", port=5000)