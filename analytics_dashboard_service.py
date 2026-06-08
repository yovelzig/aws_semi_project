from database import (
    get_support_summary,
    get_support_categories,
    get_support_interactions,
    get_knowledge_gaps,
)


def build_summary(days: int = 7) -> dict:
    return get_support_summary(days=days)


def get_categories(days: int = 7) -> list:
    return get_support_categories(days=days)


def get_interactions(days: int = 7, limit: int = 50) -> list:
    return get_support_interactions(days=days, limit=limit)


def get_dashboard_knowledge_gaps(limit: int = 50) -> list:
    return get_knowledge_gaps(limit=limit)


def get_dashboard_payload(days: int = 7) -> dict:
    return {
        "summary": build_summary(days=days),
        "categories": get_categories(days=days),
        "latestInteractions": get_interactions(days=days, limit=20),
        "knowledgeGaps": get_dashboard_knowledge_gaps(limit=20)
    }