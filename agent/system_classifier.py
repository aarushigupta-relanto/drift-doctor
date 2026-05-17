"""
Resolve monitoring mode from explicit user configuration only (no inference).
"""

from __future__ import annotations

from typing import Any

VALID_SYSTEM_TYPES = frozenset({"predictive_model", "chatbot"})


class SystemTypeRequiredError(ValueError):
    """Raised when system_type is not provided in the drift report."""


def classify_system(drift_report: dict) -> dict[str, Any]:
    """
    Read system type from user-supplied report fields only.

    Required on the report (or from ML pipeline that echoed user input):
    - ``system_type``: ``chatbot`` | ``predictive_model``
    - or ``monitoring_profile`` with the same values
    """
    candidates = [
        drift_report.get("system_type"),
        drift_report.get("monitoring_profile"),
    ]
    resolved = next((c for c in candidates if c in VALID_SYSTEM_TYPES), None)

    if resolved is None:
        raise SystemTypeRequiredError(
            "system_type is required on the drift report. "
            "Set system_type to 'chatbot' or 'predictive_model'. "
            "Automatic detection is disabled."
        )

    return {
        "system_type": resolved,
        "classification_confidence": 1.0,
        "classification_source": "user_input",
    }
