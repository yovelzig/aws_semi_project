"""
SQLite database module for persistent chat history, escalation events,
support analytics interactions, and knowledge gaps.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "database/chat_history.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS escalation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_question TEXT NOT NULL,
            assistant_answer TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS support_interactions (
            interaction_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            session_id TEXT NOT NULL,
            user_question TEXT NOT NULL,
            assistant_answer TEXT NOT NULL,
            category TEXT NOT NULL,
            resolution_type TEXT NOT NULL,
            escalated_to_it TEXT NOT NULL,
            tool_used TEXT NOT NULL,
            estimated_minutes_saved INTEGER NOT NULL,
            employee_email TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            gap_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            category TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            suggested_article_title TEXT
        )
    """)

    conn.commit()
    conn.close()


def ensure_session(session_id: str):
    conn = get_conn()
    exists = conn.execute(
        "SELECT 1 FROM sessions WHERE id=?",
        (session_id,)
    ).fetchone()

    if not exists:
        conn.execute(
            "INSERT INTO sessions VALUES (?,?)",
            (session_id, datetime.utcnow().isoformat())
        )
        conn.commit()

    conn.close()


def save_message(session_id: str, role: str, content: str):
    ensure_session(session_id)

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO messages (session_id, role, content, timestamp)
        VALUES (?,?,?,?)
        """,
        (session_id, role, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(session_id: str, limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT role, content, timestamp
        FROM messages
        WHERE session_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    conn.close()

    return [dict(r) for r in reversed(rows)]


def get_all_sessions() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, created_at FROM sessions ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def save_escalation_event(
    session_id: str,
    user_question: str,
    assistant_answer: str,
    tool_name: str,
    status: str,
    details: str = ""
):
    ensure_session(session_id)

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO escalation_events
        (session_id, user_question, assistant_answer, tool_name, status, details, timestamp)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            session_id,
            user_question,
            assistant_answer,
            tool_name,
            status,
            details,
            datetime.utcnow().isoformat()
        )
    )
    conn.commit()
    conn.close()


def get_escalation_events(limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM escalation_events
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def save_support_interaction(
    interaction_id: str,
    session_id: str,
    user_question: str,
    assistant_answer: str,
    category: str,
    resolution_type: str,
    escalated_to_it: str,
    tool_used: str,
    estimated_minutes_saved: int,
    employee_email: str = "unknown"
):
    ensure_session(session_id)

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO support_interactions
        (
            interaction_id,
            created_at,
            session_id,
            user_question,
            assistant_answer,
            category,
            resolution_type,
            escalated_to_it,
            tool_used,
            estimated_minutes_saved,
            employee_email
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            interaction_id,
            datetime.utcnow().isoformat(),
            session_id,
            user_question,
            assistant_answer,
            category,
            resolution_type,
            escalated_to_it,
            tool_used,
            estimated_minutes_saved,
            employee_email
        )
    )
    conn.commit()
    conn.close()


def get_support_interactions(days: int = 7, limit: int = 50) -> list:
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM support_interactions
        WHERE created_at >= datetime('now', ?)
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (f"-{days} days", limit)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


def get_support_categories(days: int = 7) -> list:
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT category, COUNT(*) as count
        FROM support_interactions
        WHERE created_at >= datetime('now', ?)
        GROUP BY category
        ORDER BY count DESC
        """,
        (f"-{days} days",)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


def get_support_summary(days: int = 7) -> dict:
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM support_interactions
        WHERE created_at >= datetime('now', ?)
        """,
        (f"-{days} days",)
    ).fetchall()

    conn.close()

    interactions = [dict(r) for r in rows]

    total_requests = len(interactions)

    solved_without_it = sum(
        1 for item in interactions
        if item["resolution_type"] == "SELF_SERVICE"
    )

    escalated_to_it = sum(
        1 for item in interactions
        if item["resolution_type"] == "ESCALATED_TO_IT"
        or item["escalated_to_it"].lower() == "true"
    )

    diagnostics_required = sum(
        1 for item in interactions
        if item["resolution_type"] == "DIAGNOSTICS_REQUIRED"
    )

    estimated_minutes_saved = sum(
        int(item["estimated_minutes_saved"] or 0)
        for item in interactions
    )

    self_service_rate = 0

    if total_requests:
        self_service_rate = round((solved_without_it / total_requests) * 100, 2)

    return {
        "days": days,
        "totalRequests": total_requests,
        "solvedWithoutIT": solved_without_it,
        "escalatedToIT": escalated_to_it,
        "diagnosticsRequired": diagnostics_required,
        "selfServiceRate": self_service_rate,
        "estimatedMinutesSaved": estimated_minutes_saved,
        "estimatedHoursSaved": round(estimated_minutes_saved / 60, 2)
    }


def save_knowledge_gap(
    gap_id: str,
    question: str,
    category: str,
    reason: str,
    suggested_article_title: str = ""
):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO knowledge_gaps
        (
            gap_id,
            created_at,
            question,
            category,
            reason,
            status,
            suggested_article_title
        )
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            gap_id,
            datetime.utcnow().isoformat(),
            question,
            category,
            reason,
            "OPEN",
            suggested_article_title
        )
    )
    conn.commit()
    conn.close()


def get_knowledge_gaps(limit: int = 50) -> list:
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_gaps
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]