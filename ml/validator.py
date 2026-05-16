import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pickle
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from typing import Dict, Any

from ml.model_trainer import extract_features

def validate_new_model(
    old_model_path: str,
    new_model_path: str,
    test_data_path: str,
    old_tfidf_path: str = None,
    new_tfidf_path: str = None
) -> Dict[str, Any]:
    print(f"[Validator] Validating new model: {new_model_path} against old model: {old_model_path}")
    
    try:
        df = pd.read_csv(test_data_path)
        # Use only clean rows for testing
        test_df = df[df["drift_tag"] == "clean"].dropna(subset=["user_query", "intent"])
    except FileNotFoundError:
        return {"error": f"Test data not found at {test_data_path}"}
        
    if test_df.empty:
        return {"error": "No 'clean' data found in the test dataset."}

    # Helper function to evaluate a single model
    def evaluate_model(model_path: str, model_name: str, tfidf_path: str = None) -> Dict[str, Any]:
        try:
            with open(model_path, "rb") as f:
                saved = pickle.load(f)
                model = saved["model"]
                encoder = saved["encoder"]
        except FileNotFoundError:
            raise FileNotFoundError(f"[Validator] Error: Model {model_path} not found.")

        # Load TF-IDF vectorizer
        if tfidf_path is None:
            tfidf_path = os.path.join(os.path.dirname(model_path), "tfidf_vectorizer.pkl")
        try:
            with open(tfidf_path, "rb") as f:
                tfidf = pickle.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"[Validator] Error: TFIDF vectorizer not found at {tfidf_path}.")

        # Feature extraction
        X = extract_features(test_df, vectorizer=tfidf, is_training=False)
        y_true = encoder.transform(test_df["intent"])
        
        y_pred = model.predict(X)
        
        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_true, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
        
        return {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1
        }

    try:
        old_metrics = evaluate_model(old_model_path, "old", tfidf_path=old_tfidf_path)
        new_metrics = evaluate_model(new_model_path, "new", tfidf_path=new_tfidf_path)
    except Exception as e:
        print(f"[Validator] Evaluation Error: {e}")
        return {"error": str(e)}

    old_acc = old_metrics["accuracy"]
    new_acc = new_metrics["accuracy"]
    improvement = new_acc - old_acc
    
    recommendation = "SWAP" if new_acc > old_acc + 0.01 else "KEEP"

    result = {
        "old_accuracy": round(float(old_acc), 4),
        "new_accuracy": round(float(new_acc), 4),
        "improvement": round(float(improvement), 4),
        "recommendation": recommendation,
        "metrics": {
            "old": {
                "precision": round(float(old_metrics["precision"]), 4),
                "recall": round(float(old_metrics["recall"]), 4),
                "f1": round(float(old_metrics["f1"]), 4)
            },
            "new": {
                "precision": round(float(new_metrics["precision"]), 4),
                "recall": round(float(new_metrics["recall"]), 4),
                "f1": round(float(new_metrics["f1"]), 4)
            }
        }
    }
    
    print(f"[Validator] Result: {recommendation} (Improvement: {improvement:.4f})")
    return result

if __name__ == "__main__":
    # Test script execution
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(os.path.dirname(base_dir), "final_dataset.csv")
    model_path = os.path.join(base_dir, "models", "reference_model.pkl")
    
    # Normally we'd compare two different models, but for testing we'll just compare it against itself
    if os.path.exists(model_path):
        import json
        res = validate_new_model(model_path, model_path, data_path)
        print(f"[Validator] Output:\n{json.dumps(res, indent=2)}")
    else:
        print("[Validator] Please run model_trainer.py first to create the reference model.")
