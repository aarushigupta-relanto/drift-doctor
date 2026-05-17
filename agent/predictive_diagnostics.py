"""
Predictive ML model monitoring: statistical drift, PSI, confidence, retraining signals.
"""

from __future__ import annotations

from typing import Any


def detect_predictive_drift_types(drift_report: dict) -> list[str]:
    if drift_report.get("drift_types") and drift_report.get("monitoring_pipeline") == "ml_predictive_monitor":
        return list(drift_report["drift_types"])

    drift_types: list[str] = []
    details = drift_report.get("details", {})
    confidence = details.get("confidence", {})
    intents = details.get("intent_distribution", {})

    psi_score = float(drift_report.get("psi_score", 0) or 0)
    mean_ref = float(confidence.get("mean_ref_confidence", 0) or 0)
    mean_cur = float(confidence.get("mean_cur_confidence", 0) or 0)
    confidence_drop = round(mean_ref - mean_cur, 2)

    unknown_ref = float(intents.get("unknown_pct_reference", 0) or 0)
    unknown_cur = float(intents.get("unknown_pct_current", 0) or 0)
    shifted_intents = intents.get("top_shifted_intents", []) or []

    if confidence_drop > 0.3:
        drift_types.append("confidence_drift")

    if psi_score > 0.4:
        drift_types.append("distribution_drift")

    if psi_score > 0.25:
        drift_types.append("psi_instability")

    drift_share = float(drift_report.get("drift_share", 0) or 0)
    if drift_share > 0.3:
        drift_types.append("feature_instability")

    if unknown_cur > unknown_ref:
        drift_types.append("intent_drift")

    if shifted_intents:
        drift_types.append("behavioral_drift")

    return drift_types


def assess_operational_risk(drift_report: dict, drift_types: list[str]) -> dict[str, str]:
    severity = drift_report.get("severity", "LOW")
    psi_score = float(drift_report.get("psi_score", 0) or 0)
    drift_share = float(drift_report.get("drift_share", 0) or 0)

    if severity == "HIGH" or "confidence_drift" in drift_types and psi_score > 0.4:
        operational_severity = "CRITICAL"
        production_risk = "HIGH — model reliability in production is compromised"
    elif severity == "MEDIUM" or drift_share > 0.25:
        operational_severity = "ELEVATED"
        production_risk = "MODERATE — monitor closely and plan retraining"
    else:
        operational_severity = "STABLE"
        production_risk = "LOW — within acceptable monitoring thresholds"

    retraining_necessity = "required" if (
        drift_share > 0.4 or psi_score > 0.4 or "confidence_drift" in drift_types
    ) else "recommended" if drift_types else "not_required"

    return {
        "operational_severity": operational_severity,
        "production_risk": production_risk,
        "retraining_necessity": retraining_necessity,
    }


def run_predictive_diagnosis(drift_report: dict) -> dict[str, Any]:
    drift_types = detect_predictive_drift_types(drift_report)
    risk = assess_operational_risk(drift_report, drift_types)
    details = drift_report.get("details", {})
    confidence = details.get("confidence", {})
    mean_ref = float(confidence.get("mean_ref_confidence", 0) or 0)
    mean_cur = float(confidence.get("mean_cur_confidence", 0) or 0)
    confidence_drop = round(mean_ref - mean_cur, 2)

    return {
        "system_type": "predictive_model",
        "drift_types": drift_types,
        **risk,
        "confidence_drop": confidence_drop,
        "psi_score": drift_report.get("psi_score"),
        "drift_share": drift_report.get("drift_share"),
    }
