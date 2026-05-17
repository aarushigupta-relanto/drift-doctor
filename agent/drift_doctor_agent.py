import json
import os
from pathlib import Path

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from system_classifier import classify_system
from chatbot_diagnostics import (
    run_chatbot_diagnosis,
    detect_chatbot_drift_types,
    recommend_chatbot_actions,
)
from predictive_diagnostics import (
    run_predictive_diagnosis,
    detect_predictive_drift_types,
)

load_dotenv()

_AGENT_DIR = Path(__file__).resolve().parent


class DriftDoctorAgent:
    def __init__(self):
        self.model_name = os.getenv(
            "MODEL_NAME",
            "llama-3.1-8b-instant"
        )

        self.llm = ChatGroq(
            model=self.model_name,
            temperature=0.2
        )
        self.last_report = None
        self.last_diagnosis = None
        self.last_retrain = None
        self.last_system_type = None

        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.chatbot_system_prompt = self._load_prompt("chatbot_system_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        path = _AGENT_DIR / "prompts" / filename
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def classify_system(self, drift_report: dict) -> dict:
        return classify_system(drift_report)

    def _summarize_drift_report(
        self,
        drift_report: dict,
        system_type: str,
        classification: dict,
    ) -> str:
        details = drift_report.get("details", {})
        confidence = details.get("confidence", {})
        intents = details.get("intent_distribution", {})

        severity = drift_report.get("severity")
        drift_share = drift_report.get("drift_share")
        psi_score = drift_report.get("psi_score")

        shifted_intents = intents.get("top_shifted_intents", [])

        mean_ref_conf = confidence.get("mean_ref_confidence")
        mean_cur_conf = confidence.get("mean_cur_confidence")

        unknown_ref = intents.get("unknown_pct_reference", 0)
        unknown_cur = intents.get("unknown_pct_current", 0)

        confidence_drop = None
        if mean_ref_conf is not None and mean_cur_conf is not None:
            confidence_drop = round(mean_ref_conf - mean_cur_conf, 2)

        behavioral_analysis = []

        if system_type == "chatbot":
            pipeline = drift_report.get("monitoring_pipeline", "agent_inference")
            behavioral_analysis.append(
                f"Detected system type: chatbot/RAG (confidence={classification.get('classification_confidence')}, pipeline={pipeline})."
            )
            if drift_report.get("chatbot_metrics"):
                behavioral_analysis.append(
                    f"ML chatbot metrics: {json.dumps(drift_report['chatbot_metrics'])}"
                )
            if drift_report.get("knowledge_analysis"):
                behavioral_analysis.append(
                    f"ML knowledge analysis: {json.dumps(drift_report['knowledge_analysis'])}"
                )
            behavioral_analysis.append(
                f"System type source: {classification.get('classification_source', 'user_input')}."
            )
            rule_bundle = run_chatbot_diagnosis(drift_report)
            for line in rule_bundle.get("chatbot_analysis", []):
                behavioral_analysis.append(line)
            kb = rule_bundle.get("knowledge_base_assessment", {})
            if kb.get("knowledge_base_snapshot"):
                behavioral_analysis.append(
                    f"Simulated KB snapshot: {json.dumps(kb['knowledge_base_snapshot'])}"
                )
        else:
            pipeline = drift_report.get("monitoring_pipeline", "agent_inference")
            behavioral_analysis.append(
                f"Detected system type: predictive_model (confidence={classification.get('classification_confidence')}, pipeline={pipeline})."
            )
            behavioral_analysis.append(
                f"System type source: {classification.get('classification_source', 'user_input')}."
            )
            if drift_report.get("predictive_metrics"):
                behavioral_analysis.append(
                    f"ML predictive metrics: {json.dumps(drift_report['predictive_metrics'])}"
                )
            if drift_report.get("operational_assessment"):
                behavioral_analysis.append(
                    f"ML operational assessment: {json.dumps(drift_report['operational_assessment'])}"
                )
            pred = run_predictive_diagnosis(drift_report)
            behavioral_analysis.append(
                f"Operational severity: {pred.get('operational_severity')}; "
                f"Production risk: {pred.get('production_risk')}; "
                f"Retraining: {pred.get('retraining_necessity')}."
            )

        if confidence_drop and confidence_drop > 0.3:
            behavioral_analysis.append(
                "Model confidence has dropped significantly, suggesting unfamiliar or poorly represented queries."
            )

        if unknown_cur > unknown_ref:
            behavioral_analysis.append(
                "Unknown intent rate increased — emerging user behaviors or unseen query patterns."
            )

        if shifted_intents:
            behavioral_analysis.append(
                f"Major shifts detected in intents: {', '.join(shifted_intents)}."
            )

        if psi_score and psi_score > 0.4:
            behavioral_analysis.append(
                "PSI indicates substantial distribution instability between reference and production."
            )

        summary = f"""
AI DRIFT ANALYSIS

System Type: {system_type}
Severity: {severity}
Drift Share: {drift_share}
PSI Score: {psi_score}

CONFIDENCE ANALYSIS
- Reference Confidence: {mean_ref_conf}
- Current Confidence: {mean_cur_conf}
- Confidence Drop: {confidence_drop}

INTENT ANALYSIS
- Top Shifted Intents: {shifted_intents}
- Unknown Intent % (Reference): {unknown_ref}
- Unknown Intent % (Current): {unknown_cur}

BEHAVIORAL INTERPRETATION
{chr(10).join([f"- {x}" for x in behavioral_analysis])}
"""
        return summary.strip()

    def _parse_llm_json(self, raw_response: str) -> dict:
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.replace("```", "").strip()
        return json.loads(cleaned)

    def _invoke_llm_diagnosis(
        self,
        summarized_report: str,
        system_prompt: str,
    ) -> dict:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            (
                "human",
                """
Analyze this production AI drift report.

{report}

Provide a diagnosis.
"""
            ),
        ])
        chain = prompt | self.llm | StrOutputParser()
        raw_response = chain.invoke({"report": summarized_report})
        return self._parse_llm_json(raw_response)

    def explain_drift(self, drift_report: dict) -> dict:
        """Generate root-cause analysis with adaptive system-type strategy."""
        self.last_report = drift_report

        classification = self.classify_system(drift_report)
        system_type = classification["system_type"]
        self.last_system_type = system_type

        summarized_report = self._summarize_drift_report(
            drift_report, system_type, classification
        )

        is_chatbot = system_type == "chatbot"
        prompt_text = self.chatbot_system_prompt if is_chatbot else self.system_prompt

        try:
            parsed = self._invoke_llm_diagnosis(summarized_report, prompt_text)
        except Exception as e:
            parsed = {}

        if is_chatbot:
            rule_result = run_chatbot_diagnosis(drift_report)
            ml_drift_types = drift_report.get("drift_types") or rule_result.get("drift_types", [])
            result = {
                "system_type": "chatbot",
                "monitoring_pipeline": drift_report.get("monitoring_pipeline"),
                "classification_confidence": classification.get("classification_confidence"),
                "classification_source": classification.get("classification_source", "user_input"),
                "chatbot_metrics": drift_report.get("chatbot_metrics"),
                "knowledge_analysis": drift_report.get("knowledge_analysis") or rule_result.get("knowledge_base_assessment"),
                "conversational_drift": drift_report.get("conversational_drift"),
                "response_quality": drift_report.get("response_quality"),
                "drift_types": ml_drift_types,
                "chatbot_analysis": parsed.get("chatbot_analysis")
                or rule_result.get("chatbot_analysis", []),
                "recommended_action": parsed.get("recommended_action")
                or rule_result.get("recommended_action", []),
                "knowledge_base_assessment": rule_result.get("knowledge_base_assessment"),
                "diagnosis": parsed.get("diagnosis") or rule_result.get("diagnosis", ""),
                "root_cause": parsed.get("root_cause") or rule_result.get("root_cause", ""),
                "affected_features": parsed.get("affected_features")
                or rule_result.get("affected_features", []),
                "recommendation": parsed.get("recommendation") or rule_result.get("recommendation", ""),
                "urgency": parsed.get("urgency") or rule_result.get("urgency", "UNKNOWN"),
                "confidence": parsed.get("confidence") or rule_result.get("confidence", 0.0),
            }
        else:
            pred_result = run_predictive_diagnosis(drift_report)
            drift_types = drift_report.get("drift_types") or pred_result.get("drift_types", [])
            result = {
                "system_type": "predictive_model",
                "monitoring_pipeline": drift_report.get("monitoring_pipeline"),
                "classification_confidence": classification.get("classification_confidence"),
                "classification_source": classification.get("classification_source", "user_input"),
                "predictive_metrics": drift_report.get("predictive_metrics"),
                "operational_assessment": drift_report.get("operational_assessment") or {
                    "operational_severity": pred_result.get("operational_severity"),
                    "production_risk": pred_result.get("production_risk"),
                    "retraining_necessity": pred_result.get("retraining_necessity"),
                },
                "drift_types": drift_types,
                "operational_severity": pred_result.get("operational_severity"),
                "production_risk": pred_result.get("production_risk"),
                "retraining_necessity": pred_result.get("retraining_necessity"),
                "diagnosis": parsed.get("diagnosis", ""),
                "root_cause": parsed.get("root_cause", ""),
                "affected_features": parsed.get("affected_features", []),
                "recommendation": parsed.get("recommendation", ""),
                "urgency": parsed.get("urgency", "UNKNOWN"),
                "confidence": parsed.get("confidence", 0.0),
            }

        if not parsed and not result.get("diagnosis"):
            result.update({
                "diagnosis": summarized_report[:500],
                "root_cause": "LLM parse failed; rule-based summary used",
                "recommendation": "Manual review recommended",
                "urgency": "UNKNOWN",
                "confidence": 0.0,
                "error": "LLM response could not be parsed",
            })

        self.last_diagnosis = result
        return result

    def chat(self, user_message: str, context: dict = None) -> str:
        context = context or {}
        latest_context = {
            "last_report": self.last_report,
            "last_diagnosis": self.last_diagnosis,
            "last_retrain": self.last_retrain,
            "last_system_type": self.last_system_type,
        }
        merged = {**latest_context, **context}

        system_type = (
            (merged.get("report") or {}).get("system_type")
            or merged.get("system_type")
            or self.last_system_type
            or "predictive_model"
        )
        system_role = (
            "chatbot/RAG assistant"
            if system_type == "chatbot"
            else "predictive ML model"
        )

        formatted_context = json.dumps(merged, indent=2, default=str)

        prompt = f"""
You are the AI Drift Doctor — an AI reliability engineer and MLOps copilot.

Monitored system profile: {system_role}

You help engineers understand model drift, retrieval failures, knowledge-base staleness,
retraining vs KB refresh decisions, and production AI degradation.

Current system state:
{formatted_context}

User question:
{user_message}

Rules:
- Answer the user's question directly.
- Use the monitoring context above; focus on what they asked (intents, failure, behavior, retrain, KB, risk, etc.).
- Do not repeat the same generic summary if their question is specific.
- Be concise.
"""

        response = self.llm.invoke(prompt)
        return response.content

    def _get_retraining_strategy(self, drift_types: list[str], system_type: str) -> dict:
        strategy_map = {
            "confidence_drift": {
                "strategy": "full_retraining",
                "reason": "Model confidence has degraded significantly.",
            },
            "confidence_degradation": {
                "strategy": "intent_classifier_recalibration",
                "reason": "Live query confidence is degrading on production traffic.",
            },
            "distribution_drift": {
                "strategy": "distribution_rebalancing",
                "reason": "Production feature distributions have shifted substantially.",
            },
            "psi_instability": {
                "strategy": "distribution_rebalancing",
                "reason": "PSI instability indicates production score distribution shift.",
            },
            "feature_instability": {
                "strategy": "feature_pipeline_review",
                "reason": "Monitored features show significant instability.",
            },
            "intent_drift": {
                "strategy": "intent_expansion_training",
                "reason": "New or evolving user intents detected in production traffic.",
            },
            "behavioral_drift": {
                "strategy": "recent_conversation_finetuning",
                "reason": "User interaction behavior has changed significantly.",
            },
            "conversational_drift": {
                "strategy": "targeted_conversational_finetuning",
                "reason": "Conversational patterns have shifted away from the baseline.",
            },
            "vocabulary_drift": {
                "strategy": "embedding_refresh_and_query_expansion",
                "reason": "User query vocabulary has evolved beyond training coverage.",
            },
            "semantic_drift": {
                "strategy": "retrieval_embedding_update",
                "reason": "Semantic query distribution has shifted in production.",
            },
            "retrieval_suspicion": {
                "strategy": "retrieval_pipeline_audit",
                "reason": "Degradation likely originates from retrieval, not the intent classifier.",
            },
            "possible_knowledge_staleness": {
                "strategy": "knowledge_base_refresh",
                "reason": "Issue may originate from stale retrieval or knowledge graph content rather than statistical drift.",
            },
            "possible_retrieval_or_knowledge_issue": {
                "strategy": "knowledge_base_refresh",
                "reason": "Issue may originate from stale retrieval or knowledge systems rather than statistical drift.",
            },
        }

        recommendations = []
        for drift_type in drift_types:
            if drift_type in strategy_map:
                recommendations.append({
                    "drift_type": drift_type,
                    **strategy_map[drift_type],
                })

        if system_type == "chatbot" and any(
            t in drift_types
            for t in ("possible_knowledge_staleness", "retrieval_suspicion")
        ):
            recommendations = [
                r for r in recommendations
                if r.get("strategy") != "full_retraining"
            ] or recommendations

        return {"recommended_strategies": recommendations}

    def _detect_drift_types(self, drift_report: dict, system_type: str | None = None) -> list[str]:
        if system_type is None:
            system_type = self.classify_system(drift_report)["system_type"]

        if system_type == "chatbot":
            return detect_chatbot_drift_types(drift_report)
        return detect_predictive_drift_types(drift_report)

    def suggest_retrain(self, drift_report: dict) -> dict:
        """Adaptive retrain / remediation recommendation by system type."""
        self.last_report = drift_report

        classification = self.classify_system(drift_report)
        system_type = classification["system_type"]
        self.last_system_type = system_type

        diagnosis = self.explain_drift(drift_report)
        drift_types = self._detect_drift_types(drift_report, system_type)
        strategy_recommendations = self._get_retraining_strategy(drift_types, system_type)

        drift_share = drift_report.get("drift_share", 0)
        severity = drift_report.get("severity", "LOW")
        psi_score = drift_report.get("psi_score", 0)

        details = drift_report.get("details", {})
        confidence = details.get("confidence", {})
        mean_ref_conf = confidence.get("mean_ref_confidence", 0)
        mean_cur_conf = confidence.get("mean_cur_confidence", 0)
        confidence_drop = round(mean_ref_conf - mean_cur_conf, 2)

        kb_stale = any(
            t in drift_types
            for t in ("possible_knowledge_staleness", "retrieval_suspicion")
        )

        if system_type == "chatbot":
            chatbot_actions = recommend_chatbot_actions(drift_report, drift_types)
            retrain_recommended = (
                not kb_stale
                and (drift_share > 0.35 or confidence_drop > 0.45 or severity == "HIGH")
            )
            strategy = "knowledge_refresh" if kb_stale else (
                "conversational_finetune" if severity == "HIGH" else "incremental"
            )
        else:
            chatbot_actions = []
            retrain_recommended = (
                drift_share > 0.3 or psi_score > 0.4 or confidence_drop > 0.4
            )
            strategy = "full" if severity == "HIGH" else "incremental"

        retrain_reason = []
        for rec in strategy_recommendations.get("recommended_strategies", []):
            reason = rec.get("reason")
            if reason and reason not in retrain_reason:
                retrain_reason.append(reason)

        if drift_share > 0.5:
            retrain_reason.append("Large portion of monitored features have drifted.")

        if psi_score > 0.4:
            retrain_reason.append("PSI score indicates major production distribution instability.")

        if confidence_drop > 0.4:
            retrain_reason.append(
                "Model confidence has degraded substantially compared to the reference baseline."
            )

        if confidence.get("drifted"):
            retrain_reason.append(
                "Confidence distribution drift detected through KS statistical testing."
            )

        shifted_intents = details.get("intent_distribution", {}).get("top_shifted_intents", [])
        if shifted_intents:
            retrain_reason.append(
                f"Behavioral shifts detected in intents: {', '.join(shifted_intents)}."
            )

        result = {
            **diagnosis,
            "system_type": system_type,
            "retrain_recommended": retrain_recommended,
            "retrain_strategy": strategy,
            "retrain_reason": retrain_reason,
            "confidence_drop": confidence_drop,
            "psi_score": psi_score,
            "drift_types": drift_types,
            "drift_share": drift_share,
            "strategy_recommendations": strategy_recommendations,
        }

        if system_type == "chatbot":
            result["recommended_action"] = diagnosis.get("recommended_action") or chatbot_actions
            result["chatbot_analysis"] = diagnosis.get("chatbot_analysis", [])

        self.last_retrain = result
        return result
