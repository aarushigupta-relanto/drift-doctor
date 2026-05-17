"""
Predictive ML model monitoring — PSI, KS, confidence, feature/intent distribution drift.
"""

from __future__ import annotations

import datetime
from typing import Any

import pandas as pd

from ml.drift_detector import DriftDetector


def _detect_predictive_drift_types(report: dict) -> list[str]:
    types: list[str] = []
    details = report.get("details", {})
    confidence = details.get("confidence", {})
    psi = float(report.get("psi_score", 0) or 0)
    drift_share = float(report.get("drift_share", 0) or 0)

    mean_ref = float(confidence.get("mean_ref_confidence", 0) or 0)
    mean_cur = float(confidence.get("mean_cur_confidence", 0) or 0)
    drop = mean_ref - mean_cur

    if drop > 0.3:
        types.append("confidence_drift")
    if psi > 0.4:
        types.append("distribution_drift")
        types.append("psi_instability")
    elif psi > 0.25:
        types.append("psi_instability")
    if drift_share > 0.3:
        types.append("feature_instability")

    intents = details.get("intent_distribution", {})
    if float(intents.get("unknown_pct_current", 0) or 0) > float(intents.get("unknown_pct_reference", 0) or 0):
        types.append("intent_drift")
    if intents.get("top_shifted_intents"):
        types.append("behavioral_drift")

    seen: set[str] = set()
    ordered: list[str] = []
    for dt in types:
        if dt not in seen:
            seen.add(dt)
            ordered.append(dt)
    return ordered


def _retraining_necessity(drift_types: list[str], report: dict) -> str:
    if report.get("severity") == "HIGH" or "confidence_drift" in drift_types:
        return "required"
    if drift_types:
        return "recommended"
    return "not_required"


class PredictiveMonitor:
    def __init__(
        self,
        reference_path: str | None = None,
        model_path: str | None = None,
        tfidf_path: str | None = None,
    ):
        import os

        base_dir = os.path.dirname(__file__)
        root = os.path.dirname(base_dir)
        self.reference_path = reference_path or os.path.join(root, "final_dataset.csv")
        self.model_path = model_path or os.path.join(base_dir, "models", "reference_model.pkl")
        self.tfidf_path = tfidf_path or os.path.join(base_dir, "models", "tfidf_vectorizer.pkl")
        self._detector: DriftDetector | None = None

    def _get_detector(self) -> DriftDetector:
        if self._detector is None:
            self._detector = DriftDetector(
                reference_path=self.reference_path,
                model_path=self.model_path,
                tfidf_path=self.tfidf_path,
            )
        return self._detector

    def monitor(self, current_df: pd.DataFrame) -> dict[str, Any]:
        raw = self._get_detector().detect(current_df)
        drift_types = _detect_predictive_drift_types(raw)

        return {
            **raw,
            "system_type": "predictive_model",
            "monitoring_mode": "predictive_model",
            "monitoring_pipeline": "ml_predictive_monitor",
            "drift_types": drift_types,
            "predictive_metrics": {
                "drift_share": raw.get("drift_share"),
                "psi_score": raw.get("psi_score"),
                "severity": raw.get("severity"),
                "confidence": raw.get("details", {}).get("confidence", {}),
                "intent_distribution": raw.get("details", {}).get("intent_distribution", {}),
            },
            "operational_assessment": {
                "feature_instability": "feature_instability" in drift_types,
                "model_uncertainty_elevated": "confidence_drift" in drift_types,
                "production_distribution_mismatch": "distribution_drift" in drift_types,
                "retraining_necessity": _retraining_necessity(drift_types, raw),
            },
        }


def run_predictive_monitoring(current_df: pd.DataFrame) -> dict[str, Any]:
    return PredictiveMonitor().monitor(current_df)
