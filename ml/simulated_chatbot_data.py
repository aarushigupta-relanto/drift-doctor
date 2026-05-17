"""
Simulated conversational traffic for hackathon/demo chatbot monitoring.
"""

from __future__ import annotations

REFERENCE_CONVERSATIONS: list[dict] = [
    {
        "user_query": "Hello, how are you?",
        "bot_response": "Hi! I'm doing well. How can I help you today?",
        "response_time_ms": 420,
        "confidence": 0.92,
        "feedback": "positive",
    },
    {
        "user_query": "What is your refund policy?",
        "bot_response": "Refunds are processed within 5 business days of approval.",
        "response_time_ms": 680,
        "confidence": 0.88,
        "feedback": "positive",
    },
    {
        "user_query": "How much does the pro plan cost?",
        "bot_response": "The Pro plan is $29/month billed annually.",
        "response_time_ms": 720,
        "confidence": 0.86,
        "feedback": "neutral",
    },
    {
        "user_query": "Track my order #4421",
        "bot_response": "Your order shipped yesterday via standard delivery.",
        "response_time_ms": 890,
        "confidence": 0.84,
        "feedback": "positive",
    },
    {
        "user_query": "Thanks, that helps!",
        "bot_response": "You're welcome! Let me know if you need anything else.",
        "response_time_ms": 310,
        "confidence": 0.94,
        "feedback": "positive",
    },
]

CURRENT_CONVERSATIONS: list[dict] = [
    {
        "user_query": "hey whats up",
        "bot_response": "Hello! How can I assist you?",
        "response_time_ms": 1100,
        "confidence": 0.71,
        "feedback": "neutral",
    },
    {
        "user_query": "How do I authenticate with the v2 API webhook?",
        "bot_response": "Please contact support for API documentation.",
        "response_time_ms": 1450,
        "confidence": 0.52,
        "feedback": "negative",
    },
    {
        "user_query": "Your pricing page still shows old enterprise tiers",
        "bot_response": "I'm not sure about current pricing. You may want to check the website.",
        "response_time_ms": 1320,
        "confidence": 0.48,
        "feedback": "negative",
    },
    {
        "user_query": "Can I get a refund after 60 days?",
        "bot_response": "I don't have information about refund windows.",
        "response_time_ms": 1580,
        "confidence": 0.44,
        "feedback": "negative",
    },
    {
        "user_query": "lol tell me a joke",
        "bot_response": "I'm here to help with product questions.",
        "response_time_ms": 980,
        "confidence": 0.61,
        "feedback": "neutral",
    },
    {
        "user_query": "What scopes does the OAuth token endpoint require?",
        "bot_response": "I cannot help with that request right now.",
        "response_time_ms": 1620,
        "confidence": 0.39,
        "feedback": "negative",
    },
]


def get_reference_conversations() -> list[dict]:
    return [dict(r) for r in REFERENCE_CONVERSATIONS]


def get_current_conversations() -> list[dict]:
    return [dict(r) for r in CURRENT_CONVERSATIONS]
