# Event types for the Drift Doctor system

from enum import Enum

class DriftEventType(str, Enum):
    DRIFT_DETECTED = "drift_detected"
    DRIFT_RESOLVED = "drift_resolved"
    MODEL_RETRAINED = "model_retrained"
    ALERT_TRIGGERED = "alert_triggered"
