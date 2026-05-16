import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from typing import Dict, Union, Tuple, Any

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

def train_reference_model(data_path: str) -> Dict[str, Any]:
    """
    Trains the intent classifier on the reference data and saves artifacts.
    """
    print(f"[Trainer] Loading dataset from {data_path}")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"[Trainer] Error: File {data_path} not found.")
        return {"error": f"File {data_path} not found."}

    # Filter clean rows and drop NaNs in necessary columns
    df_clean = df[df["drift_tag"] == "clean"].dropna(subset=["user_query", "intent"])
    
    if df_clean.empty:
        raise ValueError("[Trainer] No 'clean' data found to train the reference model.")

    print(f"[Trainer] Extracting features for {len(df_clean)} rows.")
    X, vectorizer = extract_features(df_clean, is_training=True)
    
    print("[Trainer] Encoding intent labels.")
    le = LabelEncoder()
    y = le.fit_transform(df_clean["intent"])
    
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
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, "reference_model.pkl")
    encoder_path = os.path.join(models_dir, "label_encoder.pkl")
    tfidf_path = os.path.join(models_dir, "tfidf_vectorizer.pkl")
    
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
        "model_path": "ml/models/reference_model.pkl",
        "n_train": len(X_train)
    }

if __name__ == "__main__":
    # Test script execution
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "final_dataset.csv")
    result = train_reference_model(dataset_path)
    print(f"[Trainer] Final Result: {result}")
