import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from typing import Dict, Union, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ml.run_config import MLRunConfig

def extract_features(df: pd.DataFrame, vectorizer: TfidfVectorizer = None, is_training: bool = False) -> Union[np.ndarray, Tuple[np.ndarray, TfidfVectorizer]]:
    """
    Engineers numeric features from the user_query text column.
    
    Returns:
        If is_training is True: tuple of (features: np.ndarray, vectorizer: TfidfVectorizer)
        If is_training is False: features: np.ndarray
    """
    queries = df['user_query'].fillna('').astype(str)
    
    query_len = queries.str.len().values
    word_count = queries.str.split().str.len().values
    avg_word_len = query_len / np.where(word_count == 0, 1, word_count)
    has_question = queries.str.endswith('?').astype(int).values
    has_greeting = queries.str.contains('hi|hello|hey', case=False, regex=True).astype(int).values
    
    if is_training:
        vectorizer = TfidfVectorizer(max_features=50)
        tfidf_features = vectorizer.fit_transform(queries).toarray()
        features = np.column_stack([query_len, word_count, avg_word_len, has_question, has_greeting, tfidf_features])
        return features, vectorizer
    else:
        if vectorizer is None:
            raise ValueError("[Trainer] A trained TfidfVectorizer must be provided when is_training is False")
        tfidf_features = vectorizer.transform(queries).toarray()
        features = np.column_stack([query_len, word_count, avg_word_len, has_question, has_greeting, tfidf_features])
        return features

def train_reference_model(
    data_path: str | None = None,
    *,
    config: Any = None,
    include_production_bridge: bool | None = None,
    production_bridge_cap: int = 250,
) -> Dict[str, Any]:
    """
    Trains the intent classifier on the reference data and saves artifacts.

    Legacy datasets may enable a production bridge + harmonization when configured.
    """
    from ml.run_config import MLRunConfig

    cfg = config if isinstance(config, MLRunConfig) else MLRunConfig.from_payload(
        {"dataset_path": data_path} if data_path else (config or {})
    )
    path = cfg.dataset_path
    use_bridge = (
        include_production_bridge
        if include_production_bridge is not None
        else cfg.legacy_harmonize
    )

    print(f"[Trainer] Loading dataset from {path}")
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"[Trainer] Error: File {path} not found.")
        return {"error": f"File {path} not found."}

    df_clean = df[df["drift_tag"] == cfg.historical_tag].dropna(
        subset=["user_query", "intent"]
    )

    if df_clean.empty:
        raise ValueError(
            f"[Trainer] No '{cfg.historical_tag}' rows found to train the reference model."
        )

    df_train = df_clean
    bridge_n = 0
    if use_bridge:
        from ml.intent_harmonizer import harmonize_production_frame

        prod_raw = df[df["drift_tag"] == cfg.production_tag].dropna(
            subset=["user_query", "intent"]
        )
        if not prod_raw.empty:
            prod = (
                harmonize_production_frame(df_clean, prod_raw)
                if cfg.legacy_harmonize
                else prod_raw
            )
            bridge_n = min(production_bridge_cap, len(prod))
            prod_sample = prod.sample(n=bridge_n, random_state=42)
            df_train = pd.concat([df_clean, prod_sample], ignore_index=True)
            print(
                f"[Trainer] Added {bridge_n} production bridge rows "
                f"({len(df_clean)} historical + {bridge_n} production)."
            )

    print(f"[Trainer] Extracting features for {len(df_train)} rows.")
    X, vectorizer = extract_features(df_train, is_training=True)
    
    print("[Trainer] Encoding intent labels.")
    le = LabelEncoder()
    y = le.fit_transform(df_train["intent"])
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("[Trainer] Training RandomForestClassifier...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = rf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"[Trainer] Test Accuracy: {accuracy:.4f}")
    
    # Save models
    models_dir = cfg.models_dir
    os.makedirs(models_dir, exist_ok=True)

    model_path = cfg.reference_model_path
    encoder_path = os.path.join(models_dir, "label_encoder.pkl")
    tfidf_path = cfg.reference_vectorizer_path
    
    # Save RF + Encoder in reference_model.pkl as specified
    saved_obj = {
        "model": rf,
        "encoder": le,
        "accuracy": accuracy
    }
    with open(model_path, "wb") as f:
        pickle.dump(saved_obj, f)
        
    # Save standalone encoder (also requested by instructions)
    with open(encoder_path, "wb") as f:
        pickle.dump(le, f)
        
    # Save standalone vectorizer
    with open(tfidf_path, "wb") as f:
        pickle.dump(vectorizer, f)
        
    print(f"[Trainer] Model saved to {model_path}")
    print(f"[Trainer] Vectorizer saved to {tfidf_path}")
    
    return {
        "accuracy": float(accuracy),
        "model_path": model_path,
        "vectorizer_path": tfidf_path,
        "dataset_path": path,
        "n_train": len(X_train),
        "n_clean": len(df_clean),
        "n_production_bridge": bridge_n,
        "run_config": cfg.to_dict(),
    }

if __name__ == "__main__":
    from ml.run_config import MLRunConfig

    result = train_reference_model(config=MLRunConfig.default())
    print(f"[Trainer] Final Result: {result}")
