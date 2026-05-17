# ML Dual Monitoring

## Architecture

```
incoming traffic + system_type (required, user-provided)
      ↓
resolve_system_type (no auto-detection)
      ↓
predictive_monitor  OR  chatbot_monitor
      ↓
enriched drift report
      ↓
agent reasoning (port 8001)
```

**You must pass `system_type`: `"chatbot"` or `"predictive_model"`.**  
The pipeline does not infer mode from data shape, intents, or metrics.

## Quick start

### Chatbot monitor (simulated data)

```bash
python -m ml.monitoring_pipeline
# or
python -c "from ml.monitoring_pipeline import run_chatbot_check; import json; print(json.dumps(run_chatbot_check(), indent=2))"
```

### Predictive monitor (requires `final_dataset.csv` + trained models)

```python
import pandas as pd
from ml.monitoring_pipeline import run_monitoring

df = pd.read_csv("final_dataset.csv")
prod = df[df["drift_tag"] == "clean_web"].head(200)
report = run_monitoring(prod, system_type="predictive_model")
```

### Unified API

```python
from ml.monitoring_pipeline import run_monitoring

# Auto-detect from record shape
run_monitoring(chatbot_records_list)
run_monitoring(prod_dataframe)

# Force mode
run_monitoring(data, system_type="chatbot")
run_monitoring(data, system_type="predictive_model", use_simulated_chatbot=True)
```

## Chatbot record format

```json
{
  "user_query": "What is your refund policy?",
  "bot_response": "Refunds are processed in 5 business days.",
  "response_time_ms": 850,
  "confidence": 0.81,
  "feedback": "negative"
}
```

## Modules

| File | Role |
|------|------|
| `monitoring_pipeline.py` | Entry point |
| `system_classifier.py` | Routes to correct monitor |
| `predictive_monitor.py` | PSI, KS, Evidently, intent drift |
| `chatbot_monitor.py` | Conversational + response quality + KB staleness |
| `simulated_chatbot_data.py` | Demo reference/current traffic |
| `knowledge_topics.py` | Simulated KB ages (days) |
| `drift_detector.py` | Low-level predictive engine |

## Backend integration

`POST /api/monitor/run` with body:

```json
{
  "system_type": "chatbot",
  "use_simulated_chatbot": true,
  "explain": true,
  "persist": true
}
```

Existing `POST /api/drift/report` still accepts enriched reports from either monitor.
