import json
import logging
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List
from http import HTTPStatus

import boto3
from boto3.dynamodb.conditions import Attr


logger = logging.getLogger()
logger.setLevel(logging.INFO)


dynamodb = boto3.resource("dynamodb")

SUPPORT_INTERACTIONS_TABLE = os.environ.get(
    "SUPPORT_INTERACTIONS_TABLE",
    "SupportInteractions"
)

KNOWLEDGE_GAPS_TABLE = os.environ.get(
    "KNOWLEDGE_GAPS_TABLE",
    "KnowledgeGaps"
)

support_interactions_table = dynamodb.Table(SUPPORT_INTERACTIONS_TABLE)
knowledge_gaps_table = dynamodb.Table(KNOWLEDGE_GAPS_TABLE)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_parameter(event: Dict[str, Any], name: str, default: str = "") -> str:
    parameters = event.get("parameters", [])

    for param in parameters:
        if param.get("name") == name:
            return str(param.get("value", default))

    return default


def build_bedrock_response(event: Dict[str, Any], text: str) -> Dict[str, Any]:
    action_group = event["actionGroup"]
    function = event["function"]
    message_ver = event.get("messageVersion", "1.0")

    return {
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": text
                    }
                }
            }
        },
        "messageVersion": message_ver
    }


def bool_from_string(value: str) -> bool:
    return str(value).strip().lower() in ["true", "1", "yes", "y"]


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def decimal_to_json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, list):
        return [decimal_to_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            key: decimal_to_json_safe(item)
            for key, item in value.items()
        }

    return value


def scan_all(table, filter_expression=None, limit: int | None = None) -> List[Dict[str, Any]]:
    items = []
    scan_kwargs = {}

    if filter_expression is not None:
        scan_kwargs["FilterExpression"] = filter_expression

    while True:
        response = table.scan(**scan_kwargs)

        items.extend(response.get("Items", []))

        if limit and len(items) >= limit:
            return items[:limit]

        last_key = response.get("LastEvaluatedKey")

        if not last_key:
            break

        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def handle_contact_it(event: Dict[str, Any]) -> str:
    user_question = get_parameter(event, "userQuestion", event.get("inputText", ""))
    assistant_answer = get_parameter(event, "assistantAnswer", "")
    issue_category = get_parameter(event, "issueCategory", "General IT")
    priority = get_parameter(event, "priority", "medium")
    employee_email = get_parameter(event, "employeeEmail", "unknown")
    session_id = get_parameter(event, "sessionId", event.get("sessionId", "unknown-session"))

    priority = priority.lower().strip()

    if priority not in ["high", "medium", "low"]:
        priority = "medium"

    it_support_email = os.environ["IT_SUPPORT_EMAIL"]
    resend_api_key = os.environ["RESEND_API_KEY"]
    resend_from_email = os.environ["RESEND_FROM_EMAIL"]

    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    subject = f"[IT Escalation] {issue_category} - Priority: {priority.upper()}"

    body = f"""
Hello IT team,

The AWS Bedrock Agent detected that this employee issue requires IT involvement.

Created At:
{created_at}

Session ID:
{session_id}

Employee Email:
{employee_email}

Issue Category:
{issue_category}

Priority:
{priority}

User Question:
{user_question}

Assistant Answer / Context:
{assistant_answer}

Required Action:
Please review this issue and contact the employee if needed.

Trigger:
ACTION_REQUIRED: CONTACT_IT
""".strip()

    payload = {
        "from": resend_from_email,
        "to": [it_support_email],
        "subject": subject,
        "text": body
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url="https://api.resend.com/emails",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "supportops-ai-lambda/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")

            logger.info(
                "Resend email success. status=%s body=%s",
                response.status,
                response_body
            )

            return "SUCCESS: The issue was escalated to IT automatically."

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")

        logger.error(
            "Resend HTTP error. status=%s body=%s",
            e.code,
            error_body
        )

        return (
            "ERROR: The issue requires IT escalation, but the automatic email failed. "
            f"Status code: {e.code}. Response: {error_body}"
        )

    except urllib.error.URLError as e:
        logger.error("Resend URL error: %s", str(e))

        return (
            "ERROR: The issue requires IT escalation, but the automatic email failed. "
            f"Response: {str(e)}"
        )


def handle_log_support_interaction(event: Dict[str, Any]) -> str:
    interaction_id = str(uuid.uuid4())
    created_at = now_iso()

    session_id = get_parameter(event, "sessionId", event.get("sessionId", "unknown-session"))
    user_question = get_parameter(event, "userQuestion", "")
    assistant_answer = get_parameter(event, "assistantAnswer", "")
    category = get_parameter(event, "category", "Unknown")
    resolution_type = get_parameter(event, "resolutionType", "UNKNOWN").strip().upper()
    escalated_to_it_raw = get_parameter(event, "escalatedToIT", "false")
    tool_used = get_parameter(event, "toolUsed", "none")
    estimated_minutes_saved_raw = get_parameter(event, "estimatedMinutesSaved", "0")
    employee_email = get_parameter(event, "employeeEmail", "unknown")

    allowed_resolution_types = {
        "SELF_SERVICE",
        "ESCALATED_TO_IT",
        "DIAGNOSTICS_REQUIRED",
        "UNKNOWN"
    }

    if resolution_type not in allowed_resolution_types:
        resolution_type = "UNKNOWN"

    escalated_to_it = bool_from_string(escalated_to_it_raw)
    estimated_minutes_saved = safe_int(estimated_minutes_saved_raw, default=0)

    item = {
        "interactionId": interaction_id,
        "createdAt": created_at,
        "sessionId": session_id,
        "userQuestion": user_question,
        "assistantAnswer": assistant_answer,
        "category": category,
        "resolutionType": resolution_type,
        "escalatedToIT": escalated_to_it,
        "toolUsed": tool_used,
        "estimatedMinutesSaved": estimated_minutes_saved,
        "employeeEmail": employee_email
    }

    support_interactions_table.put_item(Item=item)

    response = {
        "success": True,
        "message": "Support interaction logged successfully.",
        "interactionId": interaction_id,
        "resolutionType": resolution_type,
        "escalatedToIT": escalated_to_it,
        "estimatedMinutesSaved": estimated_minutes_saved
    }

    return json.dumps(response)


def handle_generate_support_analytics(event: Dict[str, Any]) -> str:
    days = safe_int(get_parameter(event, "days", "7"), default=7)

    if days <= 0:
        days = 7

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    items = scan_all(
        support_interactions_table,
        filter_expression=Attr("createdAt").gte(cutoff_iso)
    )

    total_requests = len(items)

    solved_without_it = sum(
        1 for item in items
        if item.get("resolutionType") == "SELF_SERVICE"
    )

    escalated_to_it = sum(
        1 for item in items
        if item.get("resolutionType") == "ESCALATED_TO_IT"
        or item.get("escalatedToIT") is True
    )

    diagnostics_required = sum(
        1 for item in items
        if item.get("resolutionType") == "DIAGNOSTICS_REQUIRED"
    )

    estimated_minutes_saved = 0

    for item in items:
        estimated_minutes_saved += int(item.get("estimatedMinutesSaved", 0))

    self_service_rate = 0

    if total_requests:
        self_service_rate = round((solved_without_it / total_requests) * 100, 2)

    category_counts: Dict[str, int] = {}

    for item in items:
        category = item.get("category") or "Unknown"
        category_counts[category] = category_counts.get(category, 0) + 1

    top_categories = [
        {
            "category": category,
            "count": count
        }
        for category, count in category_counts.items()
    ]

    top_categories.sort(
        key=lambda item: item["count"],
        reverse=True
    )

    latest_interactions = sorted(
        items,
        key=lambda item: item.get("createdAt", ""),
        reverse=True
    )[:10]

    analytics = {
        "success": True,
        "days": days,
        "totalRequests": total_requests,
        "solvedWithoutIT": solved_without_it,
        "escalatedToIT": escalated_to_it,
        "diagnosticsRequired": diagnostics_required,
        "selfServiceRate": self_service_rate,
        "estimatedMinutesSaved": estimated_minutes_saved,
        "estimatedHoursSaved": round(estimated_minutes_saved / 60, 2),
        "topCategories": top_categories[:10],
        "latestInteractions": decimal_to_json_safe(latest_interactions)
    }

    summary_text = [
        f"Support Analytics - Last {days} Days",
        "",
        f"Total requests: {analytics['totalRequests']}",
        f"Solved without IT: {analytics['solvedWithoutIT']}",
        f"Escalated to IT: {analytics['escalatedToIT']}",
        f"Diagnostics required: {analytics['diagnosticsRequired']}",
        f"Self-service rate: {analytics['selfServiceRate']}%",
        f"Estimated IT time saved: {analytics['estimatedHoursSaved']} hours",
        "",
        "Top categories:"
    ]

    if top_categories:
        for index, item in enumerate(top_categories[:5], start=1):
            summary_text.append(
                f"{index}. {item['category']} - {item['count']}"
            )
    else:
        summary_text.append("No categories yet.")

    summary_text.append("")
    summary_text.append("Raw JSON:")
    summary_text.append(json.dumps(decimal_to_json_safe(analytics), ensure_ascii=False))

    return "\n".join(summary_text)


def handle_detect_knowledge_gap(event: Dict[str, Any]) -> str:
    gap_id = str(uuid.uuid4())
    created_at = now_iso()

    question = get_parameter(event, "question", "")
    category = get_parameter(event, "category", "Unknown")
    reason = get_parameter(event, "reason", "Not enough information in Knowledge Base")
    suggested_article_title = get_parameter(event, "suggestedArticleTitle", "")

    item = {
        "gapId": gap_id,
        "createdAt": created_at,
        "question": question,
        "category": category,
        "reason": reason,
        "status": "OPEN",
        "suggestedArticleTitle": suggested_article_title
    }

    knowledge_gaps_table.put_item(Item=item)

    response = {
        "success": True,
        "message": "Knowledge gap logged successfully.",
        "gapId": gap_id,
        "status": "OPEN"
    }

    return json.dumps(response)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Incoming Bedrock event: %s", json.dumps(event, ensure_ascii=False))

    try:
        event["actionGroup"]
        function_name = event["function"]

        if function_name == "contactIT":
            text = handle_contact_it(event)

        elif function_name == "logSupportInteraction":
            text = handle_log_support_interaction(event)

        elif function_name == "generateSupportAnalytics":
            text = handle_generate_support_analytics(event)

        elif function_name == "detectKnowledgeGap":
            text = handle_detect_knowledge_gap(event)

        else:
            text = f"ERROR: Unknown function: {function_name}"

        return build_bedrock_response(event, text)

    except KeyError as e:
        logger.error("Missing required field or environment variable: %s", str(e))

        if "actionGroup" in event and "function" in event:
            return build_bedrock_response(
                event,
                f"ERROR: Missing required field or configuration: {str(e)}"
            )

        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "body": f"Error: missing required field/config: {str(e)}"
        }

    except Exception as e:
        logger.exception("Unexpected error in it-support-tools-lambda")

        if "actionGroup" in event and "function" in event:
            return build_bedrock_response(
                event,
                f"ERROR: Tool execution failed: {str(e)}"
            )

        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": "Internal server error"
        }