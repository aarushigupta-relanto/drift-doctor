"""
Chatbot / RAG-specific drift detection and knowledge-base freshness reasoning.
"""

from __future__ import annotations

from typing import Any

from knowledge_base import (
    assess_knowledge_freshness,
    infer_topics_from_signals,
)

CONVERSATIONAL_INTENTS = frozenset({
    "greeting", "smalltalk", "faq", "jokes", "conversation", "chitchat",
})


def _is_conversational_intent(intent: str) -> bool:
    n = intent.strip().lower().replace(" ", "_").replace("-", "_")
    if n in CONVERSATIONAL_INTENTS:
        return True
    return any(x in n for x in ("greet", "faq", "smalltalk", "chitchat"))


def detect_chatbot_drift_types(drift_report: dict) -> list[str]:
    """Detect chatbot failure modes from ML-enriched or legacy drift report."""
    ml_types = drift_report.get("drift_types")
    if ml_types and drift_report.get("monitoring_pipeline") == "ml_chatbot_monitor":
        return list(ml_types)

    drift_types: list[str] = []
    details = drift_report.get("details", {})
    confidence = details.get("confidence", {})
    intents = details.get("intent_distribution", {})

    psi_score = float(drift_report.get("psi_score", 0) or 0)
    drift_share = float(drift_report.get("drift_share", 0) or 0)
    severity = drift_report.get("severity", "LOW")

    mean_ref = float(confidence.get("mean_ref_confidence", 0) or 0)
    mean_cur = float(confidence.get("mean_cur_confidence", 0) or 0)
    confidence_drop = round(mean_ref - mean_cur, 2)

    unknown_ref = float(intents.get("unknown_pct_reference", 0) or 0)
    unknown_cur = float(intents.get("unknown_pct_current", 0) or 0)
    shifted_intents = intents.get("top_shifted_intents", []) or []

    if shifted_intents:
        drift_types.append("behavioral_drift")

    if unknown_cur > unknown_ref + 0.03:
        drift_types.append("intent_drift")

    if drift_share > 0.15:
        drift_types.append("vocabulary_drift")

    if psi_score > 0.25 or drift_share > 0.3:
        drift_types.append("semantic_drift")

    if confidence_drop > 0.2:
        drift_types.append("confidence_degradation")

    conversational = [i for i in shifted_intents if _is_conversational_intent(i)]
    if conversational or (shifted_intents and psi_score < 0.3):
        drift_types.append("conversational_drift")

    # Behavioral KB / retrieval suspicion: low statistical drift, poor signals
    if (
        confidence_drop < 0.12
        and psi_score < 0.22
        and drift_share < 0.25
        and (unknown_cur > unknown_ref or severity in ("MEDIUM", "HIGH"))
    ):
        drift_types.append("retrieval_suspicion")

    if (
        confidence_drop < 0.1
        and psi_score < 0.2
        and drift_share < 0.2
    ):
        drift_types.append("possible_knowledge_staleness")

    # Dedupe preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for dt in drift_types:
        if dt not in seen:
            seen.add(dt)
            ordered.append(dt)

    return ordered


def build_chatbot_analysis(drift_report: dict, drift_types: list[str]) -> list[str]:
    """Operational narrative lines for chatbot/RAG systems."""
    lines: list[str] = []

    metrics = drift_report.get("chatbot_metrics") or {}
    if metrics:
        lines.append(
            f"Live avg confidence {metrics.get('avg_confidence', 'n/a')} "
            f"(baseline {metrics.get('reference_avg_confidence', 'n/a')})."
        )
        if metrics.get("negative_feedback_rate", 0) > 0.2:
            lines.append(
                f"Negative feedback rate elevated at {metrics['negative_feedback_rate']:.0%}."
            )
        if metrics.get("fallback_response_rate", 0) > 0.15:
            lines.append(
                f"Fallback responses at {metrics['fallback_response_rate']:.0%} — retrieval may be failing."
            )
        if metrics.get("response_latency_ms", 0) > 1000:
            lines.append(
                f"Mean response latency {int(metrics['response_latency_ms'])}ms exceeds SLO threshold."
            )

    kb_ml = drift_report.get("knowledge_analysis") or {}
    for topic in kb_ml.get("stale_topics", []):
        age = (kb_ml.get("knowledge_topic_ages_days") or {}).get(topic)
        lines.append(f"{topic.replace('_', ' ').title()} knowledge appears stale ({age} days since update).")

    conv = drift_report.get("conversational_drift") or {}
    if conv.get("emerging_conversational_styles"):
        lines.append("Emerging conversational styles detected via vocabulary shift.")

    details = drift_report.get("details", {})
    intents = details.get("intent_distribution", {})
    confidence = details.get("confidence", {})

    shifted = intents.get("top_shifted_intents", []) or []
    unknown_ref = float(intents.get("unknown_pct_reference", 0) or 0)
    unknown_cur = float(intents.get("unknown_pct_current", 0) or 0)
    mean_ref = confidence.get("mean_ref_confidence")
    mean_cur = confidence.get("mean_cur_confidence")
    drift_share = drift_report.get("drift_share", 0)
    psi_score = drift_report.get("psi_score", 0)

    if "behavioral_drift" in drift_types or "conversational_drift" in drift_types:
        lines.append(
            "User conversational patterns have shifted significantly."
        )

    if "intent_drift" in drift_types:
        lines.append(
            "Previously unseen or underrepresented intent patterns detected in production traffic."
        )

    if "vocabulary_drift" in drift_types or drift_share and float(drift_share) > 0.15:
        lines.append(
            "Query vocabulary evolution detected — users are phrasing requests differently than the reference baseline."
        )

    if unknown_cur > unknown_ref:
        lines.append(
            f"Unknown intent rate increased from {unknown_ref:.0%} to {unknown_cur:.0%}, "
            "suggesting emerging user behaviors."
        )

    if shifted:
        lines.append(
            f"Top shifted conversational intents: {', '.join(shifted)}."
        )

    if mean_ref is not None and mean_cur is not None and mean_ref - mean_cur > 0.15:
        lines.append(
            "Classifier confidence is degrading on live queries despite potentially stable feature statistics."
        )

    if float(psi_score or 0) < 0.2 and float(drift_share or 0) < 0.25 and shifted:
        lines.append(
            "Intent distribution remains relatively stable but output quality signals may be degrading — "
            "investigate retrieval and response generation, not only the intent model."
        )

    implicated = infer_topics_from_signals(shifted, drift_types)
    kb_assessment = assess_knowledge_freshness(implicated)
    lines.extend(kb_assessment.get("findings", []))

    if "retrieval_suspicion" in drift_types and not kb_assessment.get("findings"):
        lines.append(
            "Failures may originate from stale retrieval or outdated knowledge graph content "
            "rather than statistical model drift."
        )

    if "possible_knowledge_staleness" in drift_types:
        stale = kb_assessment.get("stale_topics") or infer_topics_from_signals(shifted, drift_types)
        if stale:
            lines.append(
                "Unchanged intent distribution with degraded conversational performance "
                "suggests knowledge-base staleness over model retraining."
            )

    return lines


def recommend_chatbot_actions(
    drift_report: dict,
    drift_types: list[str],
) -> list[str]:
    """Actionable remediation for chatbot/RAG systems."""
    actions: list[str] = []
    shifted = (
        drift_report.get("details", {})
        .get("intent_distribution", {})
        .get("top_shifted_intents", [])
        or []
    )
    implicated = infer_topics_from_signals(shifted, drift_types)
    kb = assess_knowledge_freshness(implicated)

    if kb.get("kb_refresh_recommended") or "possible_knowledge_staleness" in drift_types:
        actions.append("Refresh retrieval knowledge base")
        stale = kb.get("stale_topics", [])
        if stale:
            topics_label = ", ".join(t.replace("_", " ") for t in stale)
            actions.append(f"Update stale embeddings for: {topics_label}")

    if "retrieval_suspicion" in drift_types:
        actions.append("Audit vector retrieval recall and chunk freshness for top failure intents")

    if "vocabulary_drift" in drift_types or "semantic_drift" in drift_types:
        actions.append("Update stale FAQ/API documentation embeddings")

    if "intent_drift" in drift_types or "behavioral_drift" in drift_types:
        actions.append("Perform targeted conversational fine-tuning on shifted intent clusters")

    if "confidence_degradation" in drift_types:
        actions.append("Review intent classifier calibration and low-confidence routing thresholds")

    if not actions and drift_report.get("drift_detected"):
        actions.append("Run conversational regression suite on top shifted intents before retraining")

    # Prefer KB refresh over retrain when staleness is primary signal
    if kb.get("kb_refresh_recommended") and "Perform full model retraining" not in actions:
        pass  # KB actions already prioritized
    elif (
        "possible_knowledge_staleness" not in drift_types
        and "retrieval_suspicion" not in drift_types
        and drift_report.get("severity") == "HIGH"
    ):
        actions.append("Schedule incremental intent-model retraining if KB refresh does not resolve drift")

    seen: set[str] = set()
    unique: list[str] = []
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique.append(action)
    return unique


def run_chatbot_diagnosis(drift_report: dict) -> dict[str, Any]:
    """Full chatbot diagnostic bundle (uses ML monitor output when present)."""
    drift_types = detect_chatbot_drift_types(drift_report)
    shifted = (
        drift_report.get("details", {})
        .get("intent_distribution", {})
        .get("top_shifted_intents", [])
        or []
    )
    kb_ml = drift_report.get("knowledge_analysis") or {}
    implicated = kb_ml.get("implicated_topics") or infer_topics_from_signals(shifted, drift_types)
    kb = assess_knowledge_freshness(implicated)
    if kb_ml.get("stale_topics"):
        kb["stale_topics"] = list(dict.fromkeys(kb.get("stale_topics", []) + kb_ml["stale_topics"]))
        kb["kb_refresh_recommended"] = True
        kb["stale_knowledge_suspected"] = True

    if kb.get("stale_knowledge_suspected") and "possible_knowledge_staleness" not in drift_types:
        drift_types.append("possible_knowledge_staleness")

    analysis = build_chatbot_analysis(drift_report, drift_types)
    actions = recommend_chatbot_actions(drift_report, drift_types)

    severity = drift_report.get("severity", "LOW")
    urgency_map = {"HIGH": "CRITICAL", "MEDIUM": "HIGH", "LOW": "MEDIUM"}
    urgency = urgency_map.get(severity, "MEDIUM")

    root_parts = [a for a in analysis[:2]]
    if kb.get("stale_topics"):
        root_parts.append(
            "Simulated knowledge base indicates stale content on implicated topics."
        )

    return {
        "system_type": "chatbot",
        "drift_types": drift_types,
        "chatbot_analysis": analysis,
        "recommended_action": actions,
        "knowledge_base_assessment": kb,
        "diagnosis": " ".join(analysis[:3]) if analysis else "Chatbot conversational drift detected.",
        "root_cause": " ".join(root_parts) if root_parts else "Emerging conversational drift in production traffic.",
        "affected_features": shifted or ["user_query", "intent_distribution"],
        "recommendation": "; ".join(actions[:3]) if actions else "Refresh knowledge base and audit retrieval.",
        "urgency": urgency,
        "confidence": 0.85 if drift_types else 0.5,
        "retrain_recommended": (
            "possible_knowledge_staleness" not in drift_types
            and "retrieval_suspicion" not in drift_types
            and severity == "HIGH"
        ),
    }
