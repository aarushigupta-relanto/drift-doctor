# AI Drift Doctor - ML & Drift Detection Module (Layer 2)

This directory contains the machine learning pipeline and core drift detection engine. It is designed to be easily imported by the FastAPI backend (Layer 4) and scheduled via Celery.

## 🚀 Quick Start (Testing Locally)

Before integrating, you can run these scripts individually from the root project directory to ensure the models and environment are configured correctly:

```bash
# 1. Train the reference model and generate .pkl files
python ml/model_trainer.py

# 2. Run a sample drift check on production data
python ml/drift_detector.py

# 3. Test the A/B validation script
python ml/validator.py

# 4. Run a single scheduled check loop
python ml/scheduler.py
```

## 📦 API Contract (For Backend Integration)

The backend should import and use the following functions. **All JSON schemas are strictly enforced.**

### 1. Drift Check
Used to run an immediate drift check on a batch of incoming queries.
```python
from ml.drift_detector import run_drift_check

# Pass in a Pandas DataFrame of current/production data
report_json = run_drift_check(current_df)
```

### 2. Scheduled Drift Logs
Used by the backend to fetch the most recent background drift report.
```python
from ml.scheduler import get_latest_drift_report

latest_report = get_latest_drift_report()
```

### 3. Model Validation (A/B Testing)
Used to evaluate a newly trained model against the current active model before swapping them in production.
```python
from ml.validator import validate_new_model

# Optionally pass specific TF-IDF paths if the new model uses a different vectorizer
validation_json = validate_new_model(
    old_model_path="ml/models/reference_model.pkl",
    new_model_path="ml/models/new_model.pkl",
    test_data_path="final_dataset.csv"
)
```

### 4. Feature Extraction (Shared Pipeline)
If the backend needs to explicitly extract features from queries before passing them to the model.
```python
from ml.model_trainer import extract_features

features = extract_features(df, vectorizer=loaded_tfidf_vectorizer, is_training=False)
```

## 📂 File Structure

- `model_trainer.py`: Trains the `RandomForestClassifier` on reference data.
- `drift_detector.py`: Core engine calculating Data Drift (Evidently AI), Population Stability Index (PSI), and KS tests.
- `validator.py`: Evaluates and compares the accuracy/F1 of two models on clean data.
- `scheduler.py`: Background loop that samples data periodically and triggers alerts.
- `models/`: Automatically generated directory holding the `.pkl` files (`reference_model.pkl`, `label_encoder.pkl`, `tfidf_vectorizer.pkl`).
- `reports/`: Automatically generated directory holding Evidence HTML reports and `drift_log.jsonl`.
