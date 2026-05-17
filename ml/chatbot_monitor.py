"""
Chatbot / RAG monitoring pipeline — conversational drift, response quality, KB staleness.
"""

from __future__ import annotations

import datetime
import re
from collections import Counter
from typing import Any

import numpy as np

from ml.knowledge_topics import (
    CRITICAL_STALE_DAYS,
    GENERIC_FALLBACK_PHRASES,
    GENERIC_LOW_INFO_PHRASES,
    KNOWLEDGE_TOPIC_AGE_DAYS,
    STALE_THRESHOLD_DAYS,
    TOPIC_KEYWORDS,
)

GREETING_PATTERN = re.compile(
    r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|what'?s\s+up)\b",
    re.IGNORECASE,
)
FAQ_PATTERN = re.compile(r"\b(how|what|why|can|do|does|is|are)\b.*\?", re.IGNORECASE)


def _records_to_list(data: Any) -> list[dict]:
    if isinstance(data, list):
        return data
    raise TypeError("Chatbot monitor expects a list of conversational records")


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _map_query_to_topics(query: str) -> list[str]:
    q = query.lower()
    return [topic for topic, kws in TOPIC_KEYWORDS.items() if any(kw in q for kw in kws)]


def _is_fallback_response(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in GENERIC_FALLBACK_PHRASES)


def _is_low_information(text: str) -> bool:
    t = text.lower()
    return len(t.split()) < 12 or any(p in t for p in GENERIC_LOW_INFO_PHRASES)


def _greeting_rate(records: list[dict]) -> float:
    if not records:
        return 0.0
    return sum(1 for r in records if GREETING_PATTERN.search(r.get("user_query", ""))) / len(records)


def _faq_rate(records: list[dict]) -> float:
    if not records:
        return 0.0
    return sum(1 for r in records if FAQ_PATTERN.search(r.get("user_query", ""))) / len(records)


def _avg_query_length(records: list[dict]) -> float:
    if not records:
        return 0.0
    return float(np.mean([len(r.get("user_query", "").split()) for r in records]))


def _infer_intent(query: str) -> str:
    q = query.lower()
    if GREETING_PATTERN.search(query):
        return "greeting"
    if "refund" in q:
        return "refund"
    if any(x in q for x in ("api", "webhook", "authenticate", "endpoint")):
        return "api_docs"
    if any(x in q for x in ("price", "pricing", "plan", "tier", "cost")):
        return "pricing"
    if "order" in q or "track" in q or "ship" in q:
        return "order_tracking"
    if any(x in q for x in ("joke", "lol", "haha")):
        return "chitchat"
    if FAQ_PATTERN.search(query):
        return "faq"
    return "general"


def _intent_distribution(records: list[dict]) -> dict[str, float]:
    if not records:
        return {}
    counts = Counter(_infer_intent(r.get("user_query", "")) for r in records)
    total = len(records)
    return {intent: count / total for intent, count in counts.items()}


def _intent_shift_analysis(
    reference: list[dict],
    current: list[dict],
) -> dict[str, Any]:
    ref_dist = _intent_distribution(reference)
    cur_dist = _intent_distribution(current)
    all_intents = set(ref_dist) | set(cur_dist)

    shifts: list[dict[str, Any]] = []
    for intent in all_intents:
        ref_pct = ref_dist.get(intent, 0.0)
        cur_pct = cur_dist.get(intent, 0.0)
        shifts.append(
            {
                "intent": intent,
                "reference_pct": round(ref_pct, 3),
                "current_pct": round(cur_pct, 3),
                "delta_pct": round(cur_pct - ref_pct, 3),
            }
        )
    shifts.sort(key=lambda row: abs(row["delta_pct"]), reverse=True)
    top_shifted = [row["intent"] for row in shifts[:4] if abs(row["delta_pct"]) >= 0.08]

    def _unknown_share(dist: dict[str, float]) -> float:
        return dist.get("general", 0.0) + dist.get("chitchat", 0.0)

    return {
        "top_shifted_intents": top_shifted or [row["intent"] for row in shifts[:2]],
        "intent_shifts": shifts,
        "unknown_pct_reference": round(_unknown_share(ref_dist), 2),
        "unknown_pct_current": round(_unknown_share(cur_dist), 2),
    }


def _vocabulary_drift_score(ref: list[dict], cur: list[dict]) -> float:
    ref_vocab: set[str] = set()
    cur_vocab: set[str] = set()
    for r in ref:
        ref_vocab |= _tokenize(r.get("user_query", ""))
    for r in cur:
        cur_vocab |= _tokenize(r.get("user_query", ""))
    if not ref_vocab and not cur_vocab:
        return 0.0
    union = ref_vocab | cur_vocab
    if not union:
        return 0.0
    intersection = ref_vocab & cur_vocab
    jaccard = len(intersection) / len(union)
    return round(1.0 - jaccard, 2)


def _analyze_knowledge_topics(current: list[dict]) -> dict[str, Any]:
    topic_counts: Counter[str] = Counter()
    for r in current:
        for topic in _map_query_to_topics(r.get("user_query", "")):
            topic_counts[topic] += 1

    stale_topics: list[str] = []
    implicated: list[str] = []
    for topic, count in topic_counts.most_common():
        if count == 0:
            continue
        implicated.append(topic)
        age = KNOWLEDGE_TOPIC_AGE_DAYS.get(topic, 0)
        if age >= STALE_THRESHOLD_DAYS:
            stale_topics.append(topic)

    # Critical staleness: many queries on very old topics
    critical_hits = [
        t for t in implicated
        if KNOWLEDGE_TOPIC_AGE_DAYS.get(t, 0) >= CRITICAL_STALE_DAYS
        and topic_counts[t] >= 1
    ]

    possible_staleness = bool(stale_topics) or bool(critical_hits)

    topic_detail = {
        topic: {
            "query_count": topic_counts[topic],
            "days_since_update": KNOWLEDGE_TOPIC_AGE_DAYS.get(topic),
            "is_stale": KNOWLEDGE_TOPIC_AGE_DAYS.get(topic, 0) >= STALE_THRESHOLD_DAYS,
        }
        for topic in set(implicated) | set(KNOWLEDGE_TOPIC_AGE_DAYS)
        if topic in implicated or topic in stale_topics
    }

    return {
        "stale_topics": sorted(set(stale_topics)),
        "implicated_topics": implicated,
        "topic_query_counts": dict(topic_counts),
        "topic_detail": topic_detail,
        "possible_knowledge_staleness": possible_staleness,
        "critical_stale_topics": critical_hits,
    }


def _compute_chatbot_metrics(reference: list[dict], current: list[dict]) -> dict[str, Any]:
    confs = [float(r.get("confidence", 0)) for r in current]
    ref_confs = [float(r.get("confidence", 0)) for r in reference]
    feedback = [r.get("feedback", "neutral") for r in current]
    latencies = [float(r.get("response_time_ms", 0)) for r in current]

    negative_rate = sum(1 for f in feedback if f == "negative") / max(len(feedback), 1)
    fallback_rate = sum(
        1 for r in current if _is_fallback_response(r.get("bot_response", ""))
    ) / max(len(current), 1)
    low_info_rate = sum(
        1 for r in current if _is_low_information(r.get("bot_response", ""))
    ) / max(len(current), 1)

    return {
        "avg_confidence": round(float(np.mean(confs)) if confs else 0.0, 2),
        "reference_avg_confidence": round(float(np.mean(ref_confs)) if ref_confs else 0.0, 2),
        "negative_feedback_rate": round(negative_rate, 2),
        "fallback_response_rate": round(fallback_rate, 2),
        "low_information_response_rate": round(low_info_rate, 2),
        "response_latency_ms": round(float(np.mean(latencies)) if latencies else 0.0, 0),
        "greeting_rate_current": round(_greeting_rate(current), 2),
        "greeting_rate_reference": round(_greeting_rate(reference), 2),
        "faq_pattern_rate_current": round(_faq_rate(current), 2),
        "faq_pattern_rate_reference": round(_faq_rate(reference), 2),
        "avg_query_length_current": round(_avg_query_length(current), 2),
        "avg_query_length_reference": round(_avg_query_length(reference), 2),
    }


def _detect_drift_types(
    metrics: dict[str, Any],
    conversational: dict[str, Any],
    knowledge: dict[str, Any],
) -> list[str]:
    types: list[str] = []

    if abs(metrics["greeting_rate_current"] - metrics["greeting_rate_reference"]) > 0.15:
        types.append("conversational_drift")
    if abs(metrics["faq_pattern_rate_current"] - metrics["faq_pattern_rate_reference"]) > 0.2:
        types.append("behavioral_drift")
    if abs(metrics["avg_query_length_current"] - metrics["avg_query_length_reference"]) > 2:
        types.append("vocabulary_drift")

    vocab_score = conversational.get("vocabulary_drift_score", 0)
    if vocab_score > 0.35:
        types.append("semantic_drift")

    conf_drop = metrics["reference_avg_confidence"] - metrics["avg_confidence"]
    if conf_drop > 0.15:
        types.append("confidence_collapse")
    elif conf_drop > 0.08:
        types.append("confidence_degradation")

    if metrics["negative_feedback_rate"] > 0.25:
        types.append("response_quality_degradation")
    if metrics["fallback_response_rate"] > 0.15:
        types.append("retrieval_degradation")
    if metrics["fallback_response_rate"] > 0.2 and metrics["avg_confidence"] < 0.55:
        types.append("hallucination_suspicion")
    if metrics["low_information_response_rate"] > 0.25:
        types.append("response_quality_degradation")

    if knowledge.get("possible_knowledge_staleness"):
        types.append("possible_knowledge_staleness")
    if knowledge.get("critical_stale_topics"):
        types.append("stale_knowledge_suspicion")

    seen: set[str] = set()
    ordered: list[str] = []
    for dt in types:
        if dt not in seen:
            seen.add(dt)
            ordered.append(dt)
    return ordered


def _severity(drift_types: list[str], metrics: dict[str, Any]) -> str:
    if "confidence_collapse" in drift_types or metrics["negative_feedback_rate"] > 0.4:
        return "HIGH"
    if len(drift_types) >= 3 or metrics["negative_feedback_rate"] > 0.2:
        return "MEDIUM"
    return "LOW"


def _production_risk_label(drift_types: list[str], severity: str, knowledge: dict[str, Any]) -> str:
    kb_stale = knowledge.get("possible_knowledge_staleness") or "possible_knowledge_staleness" in drift_types
    if severity == "HIGH" or "confidence_collapse" in drift_types:
        return "HIGH — retrieval/KB and response quality issues in production"
    if kb_stale and ("retrieval_degradation" in drift_types or "response_quality_degradation" in drift_types):
        return "MODERATE — likely KB staleness with retrieval degradation"
    if drift_types:
        return "ELEVATED — conversational or behavioral drift detected"
    return "LOW — within acceptable chatbot monitoring thresholds"


def _retraining_necessity(drift_types: list[str], severity: str, knowledge: dict[str, Any]) -> str:
    kb_stale = knowledge.get("possible_knowledge_staleness")
    if severity == "HIGH" or "confidence_collapse" in drift_types:
        return "required"
    if kb_stale and not any(
        t in drift_types
        for t in ("confidence_collapse", "confidence_degradation", "semantic_drift")
    ):
        return "not_required"
    if drift_types:
        return "recommended"
    return "not_required"


def _recommended_strategy(drift_types: list[str], knowledge: dict[str, Any]) -> str:
    if knowledge.get("possible_knowledge_staleness") or "possible_knowledge_staleness" in drift_types:
        return "knowledge_base_refresh"
    if "retrieval_degradation" in drift_types:
        return "retrieval_index_rebuild"
    if "confidence_collapse" in drift_types or "confidence_degradation" in drift_types:
        return "conversational_finetune"
    if drift_types:
        return "prompt_and_retrieval_tuning"
    return "monitor_only"


class ChatbotMonitor:
    """Monitor conversational AI systems using reference vs current dialogue windows."""

    def monitor(
        self,
        current: Any,
        reference: Any | None = None,
    ) -> dict[str, Any]:
        from ml.simulated_chatbot_data import get_reference_conversations

        cur = _records_to_list(current)
        ref = _records_to_list(reference) if reference is not None else get_reference_conversations()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        metrics = _compute_chatbot_metrics(ref, cur)
        vocabulary_drift_score = _vocabulary_drift_score(ref, cur)
        knowledge = _analyze_knowledge_topics(cur)

        conversational_drift = {
            "vocabulary_drift_score": vocabulary_drift_score,
            "greeting_frequency_shift": round(
                metrics["greeting_rate_current"] - metrics["greeting_rate_reference"], 2
            ),
            "faq_pattern_shift": round(
                metrics["faq_pattern_rate_current"] - metrics["faq_pattern_rate_reference"], 2
            ),
            "query_length_shift": round(
                metrics["avg_query_length_current"] - metrics["avg_query_length_reference"], 2
            ),
            "emerging_conversational_styles": vocabulary_drift_score > 0.35,
        }

        intent_analysis = _intent_shift_analysis(ref, cur)
        drift_types = _detect_drift_types(metrics, conversational_drift, knowledge)
        if intent_analysis["intent_shifts"] and abs(
            intent_analysis["intent_shifts"][0]["delta_pct"]
        ) >= 0.15:
            if "intent_drift" not in drift_types:
                drift_types.append("intent_drift")
        severity = _severity(drift_types, metrics)
        drift_detected = bool(drift_types) or knowledge.get("possible_knowledge_staleness")
        production_risk = _production_risk_label(drift_types, severity, knowledge)
        retraining_necessity = _retraining_necessity(drift_types, severity, knowledge)
        retrain_strategy = _recommended_strategy(drift_types, knowledge)
        kb_refresh = retrain_strategy == "knowledge_base_refresh"

        # Backward-compatible fields for agent / backend
        drift_share = max(vocabulary_drift_score, metrics["negative_feedback_rate"])
        psi_proxy = round(metrics["reference_avg_confidence"] - metrics["avg_confidence"], 2)

        return {
            "system_type": "chatbot",
            "monitoring_mode": "chatbot",
            "monitoring_pipeline": "ml_chatbot_monitor",
            "drift_detected": drift_detected,
            "drift_share": round(float(drift_share), 2),
            "psi_score": round(max(0.0, psi_proxy), 2),
            "severity": severity,
            "timestamp": timestamp,
            "chatbot_metrics": metrics,
            "conversational_drift": conversational_drift,
            "knowledge_analysis": {
                "stale_topics": knowledge["stale_topics"],
                "implicated_topics": knowledge["implicated_topics"],
                "topic_query_counts": knowledge["topic_query_counts"],
                "possible_knowledge_staleness": knowledge["possible_knowledge_staleness"],
                "knowledge_topic_ages_days": dict(KNOWLEDGE_TOPIC_AGE_DAYS),
            },
            "response_quality": {
                "hallucination_suspicion": "hallucination_suspicion" in drift_types,
                "retrieval_degradation": "retrieval_degradation" in drift_types,
                "confidence_collapse": "confidence_collapse" in drift_types,
            },
            "drift_types": drift_types,
            "operational_assessment": {
                "operational_severity": severity,
                "production_risk": production_risk,
                "retraining_necessity": retraining_necessity,
                "recommended_strategy": retrain_strategy,
                "kb_refresh_recommended": kb_refresh,
                "retrieval_degradation": "retrieval_degradation" in drift_types,
                "production_distribution_mismatch": vocabulary_drift_score > 0.35,
            },
            "production_risk": production_risk,
            "retraining_necessity": retraining_necessity,
            "retrain_strategy": retrain_strategy,
            "remediation": {
                "primary_action": retrain_strategy,
                "kb_topics": knowledge.get("stale_topics", []),
                "urgency": severity,
            },
            "details": {
                "confidence": {
                    "mean_ref_confidence": metrics["reference_avg_confidence"],
                    "mean_cur_confidence": metrics["avg_confidence"],
                    "drifted": metrics["avg_confidence"] < metrics["reference_avg_confidence"] - 0.1,
                },
                "intent_distribution": intent_analysis,
            },
            "report_html": None,
        }


def run_chatbot_monitoring(
    current: Any,
    reference: Any | None = None,
) -> dict[str, Any]:
    return ChatbotMonitor().monitor(current, reference)
