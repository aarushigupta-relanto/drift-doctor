import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pickle
import pandas as pd
import numpy as np
import datetime
from scipy.stats import ks_2samp
from typing import Dict, Any

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently.pipeline.column_mapping import ColumnMapping

from ml.model_trainer import extract_features

class DriftDetector:
    def __init__(self, reference_path: str, model_path: str, tfidf_path: str, drift_threshold: float = 0.2):
        print(f"[DriftDetector] Initializing with reference {reference_path}")
        try:
            full_ref = pd.read_csv(reference_path)
            self.reference = full_ref[full_ref["drift_tag"] == "clean"].dropna(subset=["user_query", "intent"]).copy()
        except FileNotFoundError:
            raise FileNotFoundError(f"[DriftDetector] Error: Data file {reference_path} not found.")

        try:
            with open(model_path, "rb") as f:
                saved = pickle.load(f)
                self.model = saved["model"]
                self.encoder = saved["encoder"]
        except FileNotFoundError:
            raise FileNotFoundError(f"[DriftDetector] Error: Model file {model_path} not found.")

        try:
            with open(tfidf_path, "rb") as f:
                self.tfidf = pickle.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"[DriftDetector] Error: TFIDF file {tfidf_path} not found.")

        self.threshold = drift_threshold
        
        # Pre-calculate reference features and confidence
        self.ref_features = extract_features(self.reference, vectorizer=self.tfidf, is_training=False)
        self.ref_proba = self.model.predict_proba(self.ref_features)
        self.ref_confidence = np.max(self.ref_proba, axis=1)
        self.ref_predictions = self.model.predict(self.ref_features)
        self.ref_intent_names = self.encoder.inverse_transform(self.ref_predictions)

    def _calculate_psi(self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        bins = np.linspace(0, 1, buckets + 1)
        expected_percents = np.histogram(expected, bins)[0] / len(expected)
        actual_percents = np.histogram(actual, bins)[0] / len(actual)
        
        # Formula: sum((actual_pct - expected_pct) * log((actual_pct + 1e-6) / (expected_pct + 1e-6)))
        psi = np.sum((actual_percents - expected_percents) * np.log((actual_percents + 1e-6) / (expected_percents + 1e-6)))
        return float(np.clip(psi, -10, 10))

    def detect(self, current_df: pd.DataFrame, generate_html: bool = False) -> Dict[str, Any]:
        try:
            print("[DriftDetector] Running drift detection...")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            
            # A. Evidently AI - Data Drift Report
            column_mapping = ColumnMapping()
            column_mapping.text_features = ["user_query"]
            
            ref_evidently = self.reference[["user_query"]].copy()
            cur_evidently = current_df[["user_query"]].copy()
            
            report = Report(metrics=[DataDriftPreset()])
            report.run(reference_data=ref_evidently, current_data=cur_evidently, column_mapping=column_mapping)
            
            evidently_dict = report.as_dict()
            dataset_drift = evidently_dict["metrics"][0]["result"]
            drift_share = dataset_drift.get("drift_share", 0.0)
            
            report_path = ""
            if generate_html:
                reports_dir = os.path.join(os.path.dirname(__file__), "reports")
                os.makedirs(reports_dir, exist_ok=True)
                report_path = os.path.join(reports_dir, f"drift_report_{timestamp.replace(':', '-')}.html")
                report.save_html(report_path)
            
            # Feature extraction for current data
            cur_features = extract_features(current_df, vectorizer=self.tfidf, is_training=False)
            
            # Run model predictions
            cur_proba = self.model.predict_proba(cur_features)
            cur_confidence = np.max(cur_proba, axis=1)
            cur_predictions = self.model.predict(cur_features)
            cur_intent_names = self.encoder.inverse_transform(cur_predictions)
            
            # B. PSI
            psi_score = self._calculate_psi(self.ref_confidence, cur_confidence)
            
            # C. KS Test
            ks_stat, p_value = ks_2samp(self.ref_confidence, cur_confidence)
            ks_drifted = bool(p_value < 0.05)
            
            # Determine severity
            if drift_share > 0.5 or psi_score > 0.4:
                severity = "HIGH"
            elif drift_share > 0.2 or psi_score > 0.2:
                severity = "MEDIUM"
            else:
                severity = "LOW"
                
            # Intent distributions
            ref_intents_series = pd.Series(self.ref_intent_names)
            cur_intents_series = pd.Series(cur_intent_names)
            
            ref_dist = ref_intents_series.value_counts(normalize=True)
            cur_dist = cur_intents_series.value_counts(normalize=True)
            
            unknown_pct_ref = ref_dist.get("unknown", 0.0)
            unknown_pct_cur = cur_dist.get("unknown", 0.0)
            
            # Top shifted intents
            all_intents = set(ref_dist.index).union(set(cur_dist.index))
            shifts = {}
            for intent in all_intents:
                r_pct = ref_dist.get(intent, 0.0)
                c_pct = cur_dist.get(intent, 0.0)
                shifts[intent] = abs(c_pct - r_pct)
                
            top_shifted = sorted(shifts.keys(), key=lambda k: shifts[k], reverse=True)[:2]
            
            result = {
                "drift_detected": bool(drift_share > self.threshold or psi_score > self.threshold or ks_drifted),
                "drift_share": round(float(drift_share), 2),
                "psi_score": round(float(psi_score), 2),
                "severity": severity,
                "details": {
                    "confidence": {
                        "ks_stat": round(float(ks_stat), 2),
                        "p_value": round(float(p_value), 4),
                        "drifted": ks_drifted,
                        "mean_ref_confidence": round(float(np.mean(self.ref_confidence)), 2),
                        "mean_cur_confidence": round(float(np.mean(cur_confidence)), 2)
                    },
                    "intent_distribution": {
                        "top_shifted_intents": top_shifted,
                        "unknown_pct_reference": round(float(unknown_pct_ref), 2),
                        "unknown_pct_current": round(float(unknown_pct_cur), 2)
                    }
                },
                "report_html": os.path.relpath(report_path, start=os.path.dirname(os.path.dirname(__file__))).replace("\\", "/") if generate_html else None,
                "timestamp": timestamp
            }
            return result
            
        except Exception as e:
            print(f"[DriftDetector] Error: {e}")
            return {"drift_detected": False, "error": str(e)}

def run_drift_check(current_df: pd.DataFrame, generate_html: bool = False) -> Dict[str, Any]:
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(os.path.dirname(base_dir), "final_dataset.csv")
    model_path = os.path.join(base_dir, "models", "reference_model.pkl")
    tfidf_path = os.path.join(base_dir, "models", "tfidf_vectorizer.pkl")
    
    detector = DriftDetector(
        reference_path=data_path,
        model_path=model_path,
        tfidf_path=tfidf_path
    )
    return detector.detect(current_df, generate_html=generate_html)

if __name__ == "__main__":
    # Test script execution
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "final_dataset.csv")
    try:
        df = pd.read_csv(dataset_path)
        cur_df = df[df["drift_tag"] == "clean_web"].head(100) # Simulating production data
        if not cur_df.empty:
            result = run_drift_check(cur_df, generate_html=False)
            
            print("\n" + "="*60)
            print("   AI DRIFT DOCTOR - TERMINAL REPORT   ")
            print("="*60)
            print(f"Status:      {'[!] DRIFT DETECTED' if result['drift_detected'] else '[OK] NO DRIFT'}")
            print(f"Severity:    {result['severity']}")
            print(f"Drift Share: {result['drift_share'] * 100}%")
            print(f"PSI Score:   {result['psi_score']}")
            print("-" * 60)
            print("   MODEL CONFIDENCE METRICS:")
            conf = result['details']['confidence']
            print(f"  Reference Mean Confidence: {conf['mean_ref_confidence']}")
            print(f"  Current Mean Confidence:   {conf['mean_cur_confidence']}")
            print(f"  KS Test p-value:           {conf['p_value']} ({'Drifted' if conf['drifted'] else 'Stable'})")
            print("-" * 60)
            print("   TOP SHIFTED INTENTS:")
            for intent in result['details']['intent_distribution']['top_shifted_intents']:
                print(f"  - {intent}")
            print("="*60 + "\n")
        else:
            print("[DriftDetector] No 'clean_web' data found for testing.")
    except Exception as e:
        print(f"[DriftDetector] Test Execution Error: {e}")
