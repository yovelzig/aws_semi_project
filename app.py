# import os
# from flask import Flask, request, jsonify

# from s3_service import upload_file_to_s3
# from bedrock_sync import trigger_kb_sync
# from rag_service import ask_question

# app = Flask(__name__)

# UPLOAD_DIR = "temp"
# os.makedirs(UPLOAD_DIR, exist_ok=True)


# @app.route("/upload", methods=["POST"])
# def upload_file():

#     file = request.files["file"]

#     local_path = os.path.join(UPLOAD_DIR, file.filename)
#     file.save(local_path)

#     # 1. Upload to S3 במקום data/
#     s3_key = f"documents/{file.filename}"
#     s3_uri = upload_file_to_s3(local_path, s3_key)

#     # 2. Trigger Bedrock Sync אוטומטי
#     sync_response = trigger_kb_sync()

#     return jsonify({
#         "message": "File uploaded & Knowledge Base syncing started",
#         "s3_uri": s3_uri,
#         "sync": sync_response
#     })


# @app.route("/ask", methods=["POST"])
# def ask():

#     question = request.json["question"]

#     answer = ask_question(question)

#     return jsonify({
#         "answer": answer
#     })

import logging
import os
import uuid

from flask import Flask, render_template, request, jsonify, session

from database import init_db, save_message, get_history

# AWS RAG
from rag_service import ask_question, retrieve_debug
from s3_service import upload_file_to_s3
from bedrock_sync import trigger_kb_sync


logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clasico-secret-key-2024")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


# -----------------------
# UI
# -----------------------
@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


# -----------------------
# CHAT (NOW AWS RAG)
# -----------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}

    question = (data.get("message") or "").strip()
    frontend_session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "Empty question"}), 400

    # Prefer session_id from frontend.
    # If missing, use Flask session.
    # If still missing, create a new one.
    session_id = frontend_session_id or session.get("session_id") or str(uuid.uuid4())
    session["session_id"] = session_id

    try:
        history = get_history(session_id, limit=10)

        llm_history = [
            {
                "role": h["role"],
                "content": h["content"]
            }
            for h in history
        ]

        # This is the important fix:
        # send both the current question and the previous conversation history.
        answer = ask_question(
            question=question,
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

# -----------------------
# HISTORY
# -----------------------
@app.route("/api/history")
def history():
    session_id = session.get("session_id")
    if not session_id:
        return jsonify([])
    return jsonify(get_history(session_id))


# -----------------------
# NEW SESSION
# -----------------------
@app.route("/api/new_session", methods=["POST"])
def new_session():
    session["session_id"] = str(uuid.uuid4())
    return jsonify({"session_id": session["session_id"]})


# -----------------------
# UPLOAD (NEW AWS FLOW)
# -----------------------
@app.route("/api/upload", methods=["POST"])
def upload_document():

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # save locally temporarily
        local_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(local_path)

        # 1. upload to S3
        s3_uri = upload_file_to_s3(
            local_path,
            f"data/{file.filename}"
        )

        # 2. trigger KB sync
        sync_response = trigger_kb_sync()

        return jsonify({
            "success": True,
            "file": file.filename,
            "s3_uri": s3_uri,
            "message": "Uploaded to S3 and Knowledge Base sync started",
            "sync": str(sync_response)
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

# -----------------------
# START
# -----------------------
if __name__ == "__main__":
    init_db()
    print("El Clásico AI (AWS RAG) ready at http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=5000)