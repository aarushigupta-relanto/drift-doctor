"""
Simulated in-memory knowledge base for behavioral freshness reasoning.
Does not connect to a real vector DB or knowledge graph.
"""

from __future__ import annotations

from typing import Any

# Topic -> human-readable staleness label (days since last update)
KNOWLEDGE_TOPICS: dict[str, str] = {
    "pricing": "updated 90 days ago",
    "refund_policy": "updated 120 days ago",
    "shipping": "updated 10 days ago",
    "api_docs": "updated 200 days ago",
}

STALE_THRESHOLD_DAYS = 60

_TOPIC_AGE_DAYS: dict[str, int] = {
    "pricing": 90,
    "refund_policy": 120,
    "shipping": 10,
    "api_docs": 200,
}

# Intent / drift-signal keywords that suggest a knowledge topic is implicated
_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing": ("pricing", "price", "cost", "billing", "plan", "subscription"),
    "refund_policy": ("refund", "return", "cancel", "policy", "warranty"),
    "shipping": ("shipping", "delivery", "tracking", "ship", "freight"),
    "api_docs": ("api", "endpoint", "documentation", "docs", "integration", "sdk"),
}


def get_knowledge_topics() -> dict[str, str]:
    return dict(KNOWLEDGE_TOPICS)


def is_topic_stale(topic: str) -> bool:
    return _TOPIC_AGE_DAYS.get(topic, 0) >= STALE_THRESHOLD_DAYS


def get_stale_topics() -> list[str]:
    return [t for t in KNOWLEDGE_TOPICS if is_topic_stale(t)]


def infer_topics_from_signals(
    shifted_intents: list[str],
    drift_types: list[str] | None = None,
) -> list[str]:
    """Map conversational intents and drift labels to likely knowledge topics."""
    topics: set[str] = set()
    combined = " ".join(shifted_intents).lower()
    if drift_types:
        combined += " " + " ".join(drift_types).lower()

    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            topics.add(topic)

    # FAQ-heavy chatbots often surface policy and API doc gaps
    if any(i.lower() in ("faq", "unknown") for i in shifted_intents):
        topics.update({"refund_policy", "api_docs"})

    return sorted(topics)


def assess_knowledge_freshness(
    implicated_topics: list[str],
) -> dict[str, Any]:
    """
    Reason about stale retrieval / KG content from simulated KB metadata.
    """
    stale_implicated = [t for t in implicated_topics if is_topic_stale(t)]
    fresh_implicated = [t for t in implicated_topics if t and not is_topic_stale(t)]

    findings: list[str] = []
    if stale_implicated:
        for topic in stale_implicated:
            findings.append(
                f"{topic.replace('_', ' ').title()} knowledge appears stale "
                f"({KNOWLEDGE_TOPICS[topic]})."
            )

    kb_refresh_recommended = bool(stale_implicated)
    suspicion = kb_refresh_recommended or (
        not implicated_topics and len(get_stale_topics()) >= 2
    )

    return {
        "implicated_topics": implicated_topics,
        "stale_topics": stale_implicated,
        "fresh_topics": fresh_implicated,
        "knowledge_base_snapshot": dict(KNOWLEDGE_TOPICS),
        "findings": findings,
        "kb_refresh_recommended": kb_refresh_recommended,
        "stale_knowledge_suspected": suspicion,
    }
