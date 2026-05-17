"""
Production-style retraining: train candidate models on clean + clean_web,
validate against reference_model.pkl, recommend SWAP vs KEEP.
"""

from __future__ import annotations

import json
import os
import pickle
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from ml.model_trainer import extract_features
from ml.run_config import MLRunConfig, default_models_dir
from ml.validator import validate_new_model, deployment_recommendation

MODELS_DIR = default_models_dir()
REFERENCE_MODEL = "reference_model.pkl"
REFERENCE_VECTORIZER = "tfidf_vectorizer.pkl"

STRATEGY_MAP: dict[str, dict[str, str]] = {
    "confidence_drift": {
        "strategy": "full_retraining",
        "reason": "confidence collapse detected",
    },
    "confidence_degradation": {
        "strategy": "full_retraining",
        "reason": "confidence collapse detected",
    },
    "distribution_drift": {
        "strategy": "distribution_rebalancing",
        "reason": "production feature distributions shifted significantly",
    },
    "feature_instability": {
        "strategy": "distribution_rebalancing",
        "reason": "production feature distributions shifted significantly",
    },
    "intent_drift": {
        "strategy": "intent_expansion_training",
        "reason": "new user intents detected",
    },
    "behavioral_drift": {
        "strategy": "recent_traffic_finetuning",
        "reason": "user behavior evolved from historical baseline",
    },
    "conversational_drift": {
        "strategy": "recent_traffic_finetuning",
        "reason": "user behavior evolved from historical baseline",
    },
    "possible_knowledge_staleness": {
        "strategy": "knowledge_refresh",
        "reason": "problem likely retrieval/knowledge related rather than statistical drift",
    },
}

STRATEGY_ALIASES = {
    "full": "full_retraining",
    "full_retraining": "full_retraining",
    "distribution_rebalancing": "distribution_rebalancing",
    "intent_expansion_training": "intent_expansion_training",
    "intent_expansion": "intent_expansion_training",
    "recent_traffic_finetuning": "recent_traffic_finetuning",
    "recent_traffic": "recent_traffic_finetuning",
    "knowledge_refresh": "knowledge_refresh",
}


def get_dataset_path() -> str:
    return MLRunConfig.default().dataset_path


def resolve_strategy(
    drift_types: list[str] | None = None,
    explicit: str | None = None,
) -> tuple[str, str]:
    """Return (strategy_key, reason)."""
    if explicit:
        key = STRATEGY_ALIASES.get(explicit.strip().lower(), explicit.strip().lower())
        if key in STRATEGY_ALIASES.values():
            for dt, meta in STRATEGY_MAP.items():
                if meta["strategy"] == key:
                    return key, meta["reason"]
            reasons = {
                "full_retraining": "manual full retrain requested",
                "distribution_rebalancing": "distribution rebalance requested",
                "intent_expansion_training": "intent expansion requested",
                "recent_traffic_finetuning": "recent traffic finetune requested",
                "knowledge_refresh": "knowledge refresh path selected",
            }
            return key, reasons.get(key, "user-selected strategy")

    for dt in drift_types or []:
        if dt in STRATEGY_MAP:
            meta = STRATEGY_MAP[dt]
            return meta["strategy"], meta["reason"]

    return "full_retraining", "default full retrain (no specific drift type)"


def align_production_intents(
    historical: pd.DataFrame,
    production: pd.DataFrame,
) -> pd.DataFrame:
    """Relabel clean_web intents using query-based harmonization (see ml/intent_harmonizer.py)."""
    from ml.intent_harmonizer import harmonize_production_frame

    return harmonize_production_frame(historical, production)


def _load_splits(
    data_path: str,
    config: MLRunConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or MLRunConfig.from_payload({"dataset_path": data_path})
    df = pd.read_csv(cfg.dataset_path)
    historical = df[df["drift_tag"] == cfg.historical_tag].dropna(
        subset=["user_query", "intent"]
    )
    production_raw = df[df["drift_tag"] == cfg.production_tag].dropna(
        subset=["user_query", "intent"]
    )
    if historical.empty:
        raise ValueError(
            f"No rows with drift_tag='{cfg.historical_tag}' in {cfg.dataset_path}."
        )
    if production_raw.empty:
        raise ValueError(
            f"No rows with drift_tag='{cfg.production_tag}' in {cfg.dataset_path}."
        )
    if cfg.legacy_harmonize:
        production = align_production_intents(historical, production_raw)
    else:
        production = production_raw.copy()
    return historical, production


def build_training_dataset(
    strategy: str,
    historical: pd.DataFrame,
    production: pd.DataFrame,
    shifted_intents: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build candidate training set from historical + production windows."""
    shifted_intents = shifted_intents or []
    meta = {
        "historical_samples": len(historical),
        "production_samples": len(production),
    }

    if strategy == "knowledge_refresh":
        return pd.concat([historical, production], ignore_index=True), meta

    if strategy == "full_retraining":
        train_df = pd.concat([historical, production], ignore_index=True)
        meta["training_samples"] = len(train_df)
        return train_df, meta

    if strategy == "distribution_rebalancing":
        # Oversample production to match intent mass in historical
        prod_parts = []
        for intent in production["intent"].unique():
            prod_i = production[production["intent"] == intent]
            hist_count = max(1, (historical["intent"] == intent).sum())
            target = max(len(prod_i), hist_count)
            if len(prod_i) < target:
                extra = prod_i.sample(n=target - len(prod_i), replace=True, random_state=42)
                prod_parts.append(pd.concat([prod_i, extra]))
            else:
                prod_parts.append(prod_i)
        prod_balanced = pd.concat(prod_parts, ignore_index=True)
        train_df = pd.concat([historical, prod_balanced], ignore_index=True)
        meta["training_samples"] = len(train_df)
        meta["rebalanced_production_samples"] = len(prod_balanced)
        return train_df, meta

    if strategy == "intent_expansion_training":
        focus = production.copy()
        focus_intents: list[str] = list(shifted_intents)
        if shifted_intents:
            focused = production[production["intent"].isin(shifted_intents)]
            if not focused.empty:
                focus = pd.concat(
                    [focused] * 3 + [production.sample(frac=0.3, random_state=42)],
                    ignore_index=True,
                )
        else:
            hist_pct = historical["intent"].value_counts(normalize=True)
            prod_pct = production["intent"].value_counts(normalize=True)
            delta = (prod_pct - hist_pct.reindex(prod_pct.index, fill_value=0)).fillna(0)
            focus_intents = delta.nlargest(3).index.tolist()
            focused = production[production["intent"].isin(focus_intents)]
            if not focused.empty:
                focus = pd.concat([focused] * 2 + [production], ignore_index=True)
        train_df = pd.concat([historical, focus], ignore_index=True)
        meta["training_samples"] = len(train_df)
        meta["focus_intents"] = focus_intents
        return train_df, meta

    if strategy == "recent_traffic_finetuning":
        # Weight toward production: duplicate production rows
        prod_boost = pd.concat([production] * 2, ignore_index=True)
        hist_sample = historical.sample(
            n=min(len(historical), len(prod_boost)),
            random_state=42,
        )
        train_df = pd.concat([hist_sample, prod_boost], ignore_index=True)
        meta["training_samples"] = len(train_df)
        return train_df, meta

    train_df = pd.concat([historical, production], ignore_index=True)
    meta["training_samples"] = len(train_df)
    return train_df, meta


def train_candidate_model(
    train_df: pd.DataFrame,
    *,
    models_dir: str = MODELS_DIR,
    stem: str | None = None,
) -> dict[str, Any]:
    """Train RandomForest candidate; save timestamped artifacts (never overwrites reference)."""
    os.makedirs(models_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    stem = stem or f"candidate_model_{stamp}"

    X, vectorizer = extract_features(train_df, is_training=True)
    le = LabelEncoder()
    y = le.fit_transform(train_df["intent"])

    split_kw: dict[str, Any] = {"test_size": 0.2, "random_state": 42}
    if len(np.unique(y)) > 1:
        split_kw["stratify"] = y
    try:
        X_train, X_val, y_train, y_val = train_test_split(X, y, **split_kw)
    except ValueError:
        split_kw.pop("stratify", None)
        X_train, X_val, y_train, y_val = train_test_split(X, y, **split_kw)

    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_val)

    metrics = {
        "accuracy": round(float(accuracy_score(y_val, y_pred)), 4),
        "precision": round(
            float(precision_score(y_val, y_pred, average="weighted", zero_division=0)), 4
        ),
        "recall": round(
            float(recall_score(y_val, y_pred, average="weighted", zero_division=0)), 4
        ),
        "f1": round(float(f1_score(y_val, y_pred, average="weighted", zero_division=0)), 4),
        "n_train": int(len(X_train)),
        "n_val": int(len(X_val)),
    }

    model_filename = f"{stem}.pkl"
    vec_filename = f"{stem}_vectorizer.pkl"
    meta_filename = f"{stem}_metadata.json"

    model_path = os.path.join(models_dir, model_filename)
    vec_path = os.path.join(models_dir, vec_filename)
    meta_path = os.path.join(models_dir, meta_filename)

    saved = {"model": rf, "encoder": le, "accuracy": metrics["accuracy"]}
    with open(model_path, "wb") as f:
        pickle.dump(saved, f)
    with open(vec_path, "wb") as f:
        pickle.dump(vectorizer, f)

    metadata = {
        "candidate_model": model_filename,
        "vectorizer": vec_filename,
        "training_metrics": metrics,
        "created_at": datetime.utcnow().isoformat(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return {
        "candidate_model": model_filename,
        "candidate_model_path": model_path,
        "vectorizer": vec_filename,
        "vectorizer_path": vec_path,
        "metadata_path": meta_path,
        "training_metrics": metrics,
        "stem": stem,
    }


def run_retraining_pipeline(
    *,
    strategy: str | None = None,
    drift_types: list[str] | None = None,
    drift_report: dict | None = None,
    data_path: str | None = None,
    config: MLRunConfig | None = None,
    on_progress: callable | None = None,
) -> dict[str, Any]:
    """
    Full pipeline: resolve strategy -> train -> validate -> recommend.
    """
    def progress(phase: str, detail: str = "") -> None:
        if on_progress:
            on_progress(phase, detail)

    cfg = config or MLRunConfig.from_payload(
        {"dataset_path": data_path} if data_path else {}
    )
    if data_path:
        cfg.dataset_path = cfg.resolve_paths().dataset_path
    drift_types = drift_types or (drift_report or {}).get("drift_types") or []
    resolved, reason = resolve_strategy(drift_types, strategy)

    shifted = []
    if drift_report:
        shifted = (
            drift_report.get("details", {})
            .get("intent_distribution", {})
            .get("top_shifted_intents", [])
            or []
        )

    progress("resolving", resolved)

    if resolved == "knowledge_refresh":
        return {
            "status": "completed",
            "strategy": resolved,
            "strategy_reason": reason,
            "training_skipped": True,
            "deployment_recommendation": {
                "decision": "KEEP CURRENT MODEL",
                "confidence": 0.85,
                "reason": (
                    "Drift signals point to retrieval/KB staleness. "
                    "Refresh knowledge base and embeddings before retraining the classifier."
                ),
            },
            "recommendation": "KEEP CURRENT MODEL",
        }

    progress("loading_data")
    historical, production = _load_splits(cfg.dataset_path, cfg)
    train_df, window_meta = build_training_dataset(
        resolved, historical, production, shifted_intents=shifted
    )
    window_meta["strategy"] = resolved

    progress("training")
    train_result = train_candidate_model(train_df, models_dir=cfg.models_dir)

    if not os.path.isfile(cfg.reference_model_path):
        raise FileNotFoundError(
            f"Reference model missing at {cfg.reference_model_path}. "
            "Train reference model first: python -m ml.model_trainer"
        )

    progress("validating")
    validation = validate_new_model(
        old_model_path=cfg.reference_model_path,
        new_model_path=train_result["candidate_model_path"],
        test_data_path=cfg.dataset_path,
        old_tfidf_path=cfg.reference_vectorizer_path,
        new_tfidf_path=train_result["vectorizer_path"],
        test_drift_tag=cfg.production_tag,
        legacy_harmonize=cfg.legacy_harmonize,
        historical_tag=cfg.historical_tag,
    )

    if validation.get("error"):
        return {"status": "failed", "error": validation["error"], "strategy": resolved}

    deploy = validation.get("deployment_recommendation") or deployment_recommendation(
        validation.get("metrics", {}).get("old", {}),
        validation.get("metrics", {}).get("new", {}),
    )

    report = {
        "status": "completed",
        "strategy": resolved,
        "strategy_reason": reason,
        "run_config": cfg.to_dict(),
        "candidate_model": train_result["candidate_model"],
        "training_metrics": train_result["training_metrics"],
        "training_window": window_meta,
        "validation_metrics": {
            "old_accuracy": validation["old_accuracy"],
            "new_accuracy": validation["new_accuracy"],
            "improvement": validation["improvement"],
            "precision_delta": validation.get("precision_delta", 0),
            "recall_delta": validation.get("recall_delta", 0),
            "f1_delta": validation.get("f1_delta", 0),
            "validation_window": validation.get("validation_window"),
            "validation_note": validation.get("validation_note"),
            "baseline_validation": validation.get("baseline_validation"),
        },
        "metrics": validation.get("metrics"),
        "deployment_recommendation": deploy,
        "recommendation": deploy.get("decision", validation.get("recommendation")),
        "validation": validation,
    }
    progress("completed")
    return report
