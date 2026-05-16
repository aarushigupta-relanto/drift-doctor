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

        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def _summarize_drift_report(self, drift_report: dict) -> str:
        """
        Convert raw drift JSON into cleaner context for the LLM.
        """

        details = drift_report.get("details", {})

        drifted_features = []
        stable_features = []

        for feature, metrics in details.items():
            if metrics.get("drifted"):
                drifted_features.append(
                    f"- {feature}: DRIFTED "
                    f"(p_value={metrics.get('p_value')}, "
                    f"ks_stat={metrics.get('ks_stat')})"
                )
            else:
                stable_features.append(
                    f"- {feature}: stable "
                    f"(p_value={metrics.get('p_value')})"
                )
        possible_causes = []

        if "confidence" in details:
            possible_causes.append(
                "- Confidence degradation suggests unseen or poorly represented queries."
            )

        if "intent_distribution" in details:
            possible_causes.append(
                "- Intent distribution shift suggests changing user behavior or emerging trends."
            )

        if "response_time_ms" in details:
            possible_causes.append(
                "- Increased response latency may indicate inference or infrastructure bottlenecks."
            )
        summary = f"""
        DRIFT REPORT SUMMARY

        Drift Detected: {drift_report.get('drift_detected')}
        Severity: {drift_report.get('severity')}
        Drift Share: {drift_report.get('drift_share')}

        DRIFTED FEATURES:
        {chr(10).join(drifted_features) if drifted_features else 'None'}

        STABLE FEATURES:
        {chr(10).join(stable_features) if stable_features else 'None'}

        POSSIBLE INTERPRETATIONS:
        {chr(10).join(possible_causes) if possible_causes else 'No strong indicators detected.'}
        """

        return summary.strip()

    def explain_drift(self, drift_report: dict) -> dict:
        """
        Generate root-cause analysis for detected drift.
        """

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

        formatted_context = json.dumps(context, indent=2)

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

    def suggest_retrain(self, drift_report: dict) -> dict:
        """
        Decide whether retraining is required and recommend a strategy.
        """

        diagnosis = self.explain_drift(drift_report)

        drift_share = drift_report.get("drift_share", 0)
        severity = drift_report.get("severity", "LOW")

        retrain_recommended = drift_share > 0.3

        if severity == "HIGH":
            strategy = "full"
        else:
            strategy = "incremental"

        retrain_reason = []

        if drift_share > 0.5:
            retrain_reason.append(
                "Large portion of monitored features have drifted."
            )

        details = drift_report.get("details", {})

        if "confidence" in details and details["confidence"].get("drifted"):
            retrain_reason.append(
                "Model confidence degradation detected."
            )

        if "intent_distribution" in details and details["intent_distribution"].get("drifted"):
            retrain_reason.append(
                "User intent distribution has shifted significantly."
            )

        return {
            **diagnosis,
            "retrain_recommended": retrain_recommended,
            "retrain_strategy": strategy,
            "retrain_reason": retrain_reason
        }
