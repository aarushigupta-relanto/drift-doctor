"""Simulated knowledge-base metadata (days since last update)."""

KNOWLEDGE_TOPIC_AGE_DAYS: dict[str, int] = {
    "pricing": 90,
    "refund_policy": 120,
    "shipping": 10,
    "api_docs": 200,
}

STALE_THRESHOLD_DAYS = 60
CRITICAL_STALE_DAYS = 180

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing": ("price", "pricing", "cost", "billing", "plan", "subscription"),
    "refund_policy": ("refund", "return", "cancel", "policy", "warranty"),
    "shipping": ("shipping", "delivery", "tracking", "ship", "freight"),
    "api_docs": ("api", "endpoint", "documentation", "docs", "integration", "sdk"),
}

GENERIC_FALLBACK_PHRASES = (
    "i don't know",
    "i'm not sure",
    "i cannot help",
    "please contact support",
    "i do not have information",
    "unable to answer",
)

GENERIC_LOW_INFO_PHRASES = (
    "here is some information",
    "you may want to check",
    "generally speaking",
)
