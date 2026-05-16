import json
import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


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
        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def _summarize_drift_report(self, drift_report: dict) -> str:
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

        if mean_ref_conf and mean_cur_conf:
            confidence_drop = round(mean_ref_conf - mean_cur_conf, 2)

        behavioral_analysis = []

        if confidence_drop and confidence_drop > 0.3:
            behavioral_analysis.append(
                "Model confidence has dropped significantly, suggesting the model is encountering unfamiliar or poorly represented queries."
            )

            behavioral_analysis.append(
                "This may indicate vocabulary drift, unseen semantic patterns, or insufficient training coverage for current production traffic."
            )

        if unknown_cur > unknown_ref:
            behavioral_analysis.append(
                "The percentage of unknown intents has increased, indicating emerging user behaviors or unseen query patterns."
            )

            behavioral_analysis.append(
                "Production traffic may now contain intents that were absent or underrepresented during training."
            )

        if shifted_intents:
            behavioral_analysis.append(
                f"Major behavioral shifts detected in intents: {', '.join(shifted_intents)}."
            )

            behavioral_analysis.append(
                "User interaction patterns appear to be evolving away from the historical baseline distribution."
            )

        if psi_score and psi_score > 0.4:
            behavioral_analysis.append(
                "PSI score indicates substantial distribution instability between reference and production traffic."
            )

            behavioral_analysis.append(
                "Feature distributions have shifted enough to potentially reduce model reliability in production."
            )

        
        summary = f"""
    AI DRIFT ANALYSIS

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

    def explain_drift(self, drift_report: dict) -> dict:
        """
        Generate root-cause analysis for detected drift.
        """

        self.last_report = drift_report
        self.last_diagnosis = None
        summarized_report = self._summarize_drift_report(drift_report)

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            (
                "human",
                """
Analyze this ML drift report.

{report}

Provide a diagnosis.
"""
            )
        ])

        chain = prompt | self.llm | StrOutputParser()

        raw_response = chain.invoke({
            "report": summarized_report
        })

        try:
            cleaned = raw_response.strip()

            if cleaned.startswith("```json"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

            elif cleaned.startswith("```"):
                cleaned = cleaned.replace("```", "").strip()

            parsed = json.loads(cleaned)

            return {
                "diagnosis": parsed.get("diagnosis", ""),
                "root_cause": parsed.get("root_cause", ""),
                "affected_features": parsed.get("affected_features", []),
                "recommendation": parsed.get("recommendation", ""),
                "urgency": parsed.get("urgency", "UNKNOWN"),
                "confidence": parsed.get("confidence", 0.0)
            }

        except Exception as e:
            return {
                "diagnosis": raw_response,
                "root_cause": "Unable to parse structured response",
                "affected_features": [],
                "recommendation": "Manual review recommended",
                "urgency": "UNKNOWN",
                "confidence": 0.0,
                "error": str(e)
            }

    def chat(self, user_message: str, context: dict = None) -> str:
        """
        Conversational assistant for model health and drift analysis.
        """

        context = context or {}
        latest_context = {
            "last_report": self.last_report,
            "last_diagnosis": self.last_diagnosis,
            "last_retrain": self.last_retrain
        }

        formatted_context = json.dumps(
            context if context else latest_context,
            indent=2
        )

        prompt = f"""
    You are the AI Drift Doctor conversational assistant.

    You help engineers understand:
    - model drift
    - degraded confidence
    - retraining decisions
    - production AI failures
    - changing user behavior

    Current system state:
    {formatted_context}

    LATEST SYSTEM STATE:
    {json.dumps(latest_context, indent=2)}

    User question:
    {user_message}

    Rules:
    - Be concise and operational.
    - Use the provided system context.
    - Avoid generic AI explanations.
    - Explain technical issues clearly.
    - If drift severity is HIGH, emphasize urgency.
    - Keep responses under 6 sentences.
    """

        response = self.llm.invoke(prompt)

        return response.content

    def _get_retraining_strategy(
        self,
        drift_types: list[str]
    ) -> dict:
            strategy_map = {
                "confidence_drift": {
                    "strategy": "full_retraining",
                    "reason": "Model confidence has degraded significantly."
                },

                "distribution_drift": {
                    "strategy": "distribution_rebalancing",
                    "reason": "Production feature distributions have shifted substantially."
                },

                "intent_drift": {
                    "strategy": "intent_expansion_training",
                    "reason": "New or evolving user intents detected in production traffic."
                },

                "behavioral_drift": {
                    "strategy": "recent_conversation_finetuning",
                    "reason": "User interaction behavior has changed significantly."
                },

                "possible_retrieval_or_knowledge_issue": {
                    "strategy": "knowledge_base_refresh",
                    "reason": "Issue may originate from stale retrieval or knowledge systems rather than statistical drift."
                }
            }

            recommendations = []

            for drift_type in drift_types:
                if drift_type in strategy_map:
                    recommendations.append({
                        "drift_type": drift_type,
                        **strategy_map[drift_type]
                    })

            return {
                "recommended_strategies": recommendations
            }
    
    def _detect_drift_types(self, drift_report: dict) -> list[str]:

        drift_types = []

        details = drift_report.get("details", {})

        confidence = details.get("confidence", {})
        intents = details.get("intent_distribution", {})

        psi_score = drift_report.get("psi_score", 0)

        mean_ref_conf = confidence.get("mean_ref_confidence", 0)
        mean_cur_conf = confidence.get("mean_cur_confidence", 0)

        confidence_drop = round(
            mean_ref_conf - mean_cur_conf,
            2
        )

        unknown_ref = intents.get("unknown_pct_reference", 0)
        unknown_cur = intents.get("unknown_pct_current", 0)

        shifted_intents = intents.get(
            "top_shifted_intents",
            []
        )

        # Confidence Drift
        if confidence_drop > 0.3:
            drift_types.append("confidence_drift")

        # Distribution Drift
        if psi_score > 0.4:
            drift_types.append("distribution_drift")

        # Intent Drift
        if unknown_cur > unknown_ref:
            drift_types.append("intent_drift")

        # Behavioral Drift
        if shifted_intents:
            drift_types.append("behavioral_drift")

        # Retrieval / KG Suspicion
        if (
            confidence_drop < 0.1
            and psi_score < 0.2
            and drift_report.get("severity") == "LOW"
        ):
            drift_types.append("possible_retrieval_or_knowledge_issue")

        return drift_types
    
    
    def suggest_retrain(self, drift_report: dict) -> dict:
        """
        Decide whether retraining is required and recommend a strategy.
        """
        self.last_report = drift_report

        diagnosis = self.explain_drift(drift_report)
        drift_types = self._detect_drift_types(drift_report)
        strategy_recommendations = self._get_retraining_strategy(drift_types)

        drift_share = drift_report.get("drift_share", 0)
        severity = drift_report.get("severity", "LOW")
        psi_score = drift_report.get("psi_score", 0)

        details = drift_report.get("details", {})
        confidence = details.get("confidence", {})
        mean_ref_conf = confidence.get("mean_ref_confidence", 0)
        mean_cur_conf = confidence.get("mean_cur_confidence", 0)
        confidence_drop = round(mean_ref_conf - mean_cur_conf, 2)

        retrain_recommended = (
            drift_share > 0.3 or psi_score > 0.4 or confidence_drop > 0.4
        )

        strategy = "full" if severity == "HIGH" else "incremental"

        retrain_reason = []

        # Add strategy-based reasons first (avoids duplicating detection logic)
        for rec in strategy_recommendations.get("recommended_strategies", []):
            reason = rec.get("reason")
            if reason and reason not in retrain_reason:
                retrain_reason.append(reason)

        # Add other concrete signals
        if drift_share > 0.5 and "Large portion of monitored features have drifted." not in retrain_reason:
            retrain_reason.append("Large portion of monitored features have drifted.")

        if psi_score > 0.4 and "PSI score indicates major production distribution instability." not in retrain_reason:
            retrain_reason.append("PSI score indicates major production distribution instability.")

        if confidence_drop > 0.4 and "Model confidence has degraded substantially compared to the reference baseline." not in retrain_reason:
            retrain_reason.append("Model confidence has degraded substantially compared to the reference baseline.")

        if confidence.get("drifted") and "Confidence distribution drift detected through KS statistical testing." not in retrain_reason:
            retrain_reason.append("Confidence distribution drift detected through KS statistical testing.")

        shifted_intents = details.get("intent_distribution", {}).get("top_shifted_intents", [])
        if shifted_intents:
            intent_reason = f"Behavioral shifts detected in intents: {', '.join(shifted_intents)}."
            if intent_reason not in retrain_reason:
                retrain_reason.append(intent_reason)

        result = {
            **diagnosis,
            "retrain_recommended": retrain_recommended,
            "retrain_strategy": strategy,
            "retrain_reason": retrain_reason,
            "confidence_drop": confidence_drop,
            "psi_score": psi_score,
            "drift_types": drift_types,
            "drift_share": drift_share,
            "strategy_recommendations": strategy_recommendations,
        }

        self.last_retrain = result
        return result
    
    