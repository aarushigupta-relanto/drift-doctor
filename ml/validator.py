import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pickle

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from typing import Any, Dict

from ml.model_trainer import extract_features


def deployment_recommendation(
    old_metrics: Dict[str, float],
    new_metrics: Dict[str, float],
    *,
    precision_regression_threshold: float = 0.05,
    min_f1_gain: float = 0.0,
) -> Dict[str, Any]:
    """
    Recommend SWAP vs KEEP CURRENT MODEL based on metric deltas.
    """
    old_acc = old_metrics.get("accuracy", 0.0)
    new_acc = new_metrics.get("accuracy", 0.0)
    old_f1 = old_metrics.get("f1", 0.0)
    new_f1 = new_metrics.get("f1", 0.0)
    old_prec = old_metrics.get("precision", 0.0)
    new_prec = new_metrics.get("precision", 0.0)

    acc_improved = new_acc > old_acc
    f1_improved = new_f1 >= old_f1 + min_f1_gain
    severe_prec_regression = new_prec < old_prec - precision_regression_threshold

    f1_delta = new_f1 - old_f1
    acc_delta = new_acc - old_acc

    if acc_improved and f1_improved and not severe_prec_regression:
        reason = (
            f"Candidate model improved accuracy by {acc_delta:.1%} and F1 by {f1_delta:.1%} "
            f"with no severe precision regression."
        )
        confidence = min(0.99, 0.75 + abs(f1_delta) + abs(acc_delta))
        return {
            "decision": "SWAP",
            "confidence": round(confidence, 2),
            "reason": reason,
        }

    parts = []
    if not acc_improved:
        parts.append(f"accuracy did not improve ({old_acc:.2%} vs {new_acc:.2%})")
    if not f1_improved:
        parts.append(f"F1 did not improve ({old_f1:.2%} vs {new_f1:.2%})")
    if severe_prec_regression:
        parts.append(
            f"precision regressed by more than {precision_regression_threshold:.0%}"
        )
    reason = "Keeping current model: " + "; ".join(parts) + "."
    return {
        "decision": "KEEP CURRENT MODEL",
        "confidence": round(0.7 + min(0.25, abs(acc_delta)), 2),
        "reason": reason,
    }


def validate_new_model(
    old_model_path: str,
    new_model_path: str,
    test_data_path: str,
    old_tfidf_path: str | None = None,
    new_tfidf_path: str | None = None,
    test_drift_tag: str = "clean_web",
    *,
    legacy_harmonize: bool = False,
    historical_tag: str = "clean",
) -> Dict[str, Any]:
    """
    Compare deployed (reference) model vs candidate on a held-out production window.
    """
    print(
        f"[Validator] Validating {new_model_path} against {old_model_path} "
        f"on drift_tag={test_drift_tag}"
    )

    try:
        from ml.intent_harmonizer import harmonize_production_frame

        df = pd.read_csv(test_data_path)
        historical = df[df["drift_tag"] == historical_tag].dropna(
            subset=["user_query", "intent"]
        )
        test_df = df[df["drift_tag"] == test_drift_tag].dropna(
            subset=["user_query", "intent"]
        )
        if legacy_harmonize and not historical.empty and not test_df.empty:
            test_df = harmonize_production_frame(historical, test_df)
        if test_df.empty and test_drift_tag != historical_tag:
            test_df = historical.copy()
    except FileNotFoundError:
        return {"error": f"Test data not found at {test_data_path}"}

    if test_df.empty:
        return {"error": f"No rows with drift_tag='{test_drift_tag}' for validation."}

    def load_artifacts(model_path: str, tfidf_path: str | None):
        with open(model_path, "rb") as f:
            saved = pickle.load(f)
        if tfidf_path is None:
            tfidf_path = os.path.join(os.path.dirname(model_path), "tfidf_vectorizer.pkl")
        with open(tfidf_path, "rb") as f:
            tfidf = pickle.load(f)
        return saved["model"], saved["encoder"], tfidf

    old_model, old_encoder, old_tfidf = load_artifacts(old_model_path, old_tfidf_path)
    new_model, new_encoder, new_tfidf = load_artifacts(new_model_path, new_tfidf_path)

    common_intents = set(old_encoder.classes_) & set(new_encoder.classes_)
    eval_df = test_df[test_df["intent"].isin(common_intents)]
    if eval_df.empty:
        return {
            "error": "No overlapping intent labels between reference and candidate on the validation window.",
        }

    def evaluate_df(
        model,
        encoder,
        tfidf,
        frame: pd.DataFrame,
    ) -> Dict[str, float]:
        subset = frame[frame["intent"].isin(encoder.classes_)]
        if subset.empty:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
        X = extract_features(subset, vectorizer=tfidf, is_training=False)
        y_true = encoder.transform(subset["intent"])
        y_pred = model.predict(X)
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(
                precision_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "recall": float(
                recall_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        }

    def evaluate_on_window(model, encoder, tfidf) -> Dict[str, float]:
        return evaluate_df(model, encoder, tfidf, eval_df)

    try:
        old_metrics = evaluate_on_window(old_model, old_encoder, old_tfidf)
        new_metrics = evaluate_on_window(new_model, new_encoder, new_tfidf)
    except Exception as e:
        print(f"[Validator] Evaluation Error: {e}")
        return {"error": str(e)}

    old_acc = old_metrics["accuracy"]
    new_acc = new_metrics["accuracy"]
    improvement = new_acc - old_acc
    prec_delta = new_metrics["precision"] - old_metrics["precision"]
    rec_delta = new_metrics["recall"] - old_metrics["recall"]
    f1_delta = new_metrics["f1"] - old_metrics["f1"]

    deploy = deployment_recommendation(old_metrics, new_metrics)
    recommendation = "SWAP" if deploy["decision"] == "SWAP" else "KEEP"

    result = {
        "old_accuracy": round(old_acc, 4),
        "new_accuracy": round(new_acc, 4),
        "improvement": round(improvement, 4),
        "precision_delta": round(prec_delta, 4),
        "recall_delta": round(rec_delta, 4),
        "f1_delta": round(f1_delta, 4),
        "recommendation": recommendation,
        "metrics": {
            "old": {k: round(v, 4) for k, v in old_metrics.items()},
            "new": {k: round(v, 4) for k, v in new_metrics.items()},
        },
        "deployment_recommendation": deploy,
        "test_samples": len(eval_df),
        "test_samples_total": len(test_df),
        "test_drift_tag": test_drift_tag,
        "validation_window": "simulated_production (clean_web)",
    }

    if test_drift_tag == "clean_web" and not historical.empty:
        baseline_n = min(400, len(historical))
        baseline_df = historical.sample(n=baseline_n, random_state=42)
        deployed_baseline = evaluate_df(old_model, old_encoder, old_tfidf, baseline_df)
        result["baseline_validation"] = {
            "window": "historical (clean)",
            "samples": baseline_n,
            "deployed_accuracy": round(deployed_baseline["accuracy"], 4),
            "deployed_f1": round(deployed_baseline["f1"], 4),
        }
        if legacy_harmonize:
            result["validation_note"] = (
                "Legacy dataset: production labels were harmonized to the historical taxonomy. "
                "Deployed accuracy on clean_web may be low if the reference was trained only on clean."
            )
        else:
            result["validation_note"] = (
                f"Validation on production window ({test_drift_tag}) with aligned intents. "
                "Candidate was trained on historical + production rows; see baseline_validation "
                f"for deployed performance on {historical_tag} only."
            )

    print(f"[Validator] Result: {deploy['decision']} (delta acc={improvement:.4f}, f1={f1_delta:.4f})")
    return result
