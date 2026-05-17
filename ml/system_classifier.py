"""
Resolve monitoring mode from explicit user configuration only (no inference).
"""

from __future__ import annotations

from typing import Any, Literal

SystemType = Literal["predictive_model", "chatbot"]

VALID_SYSTEM_TYPES = frozenset({"predictive_model", "chatbot"})


class SystemTypeRequiredError(ValueError):
    """Raised when system_type is not provided by the caller."""


def resolve_system_type(
    *,
    system_type: str | None = None,
    monitoring_profile: str | None = None,
    report: dict | None = None,
) -> dict[str, Any]:
    """
    Resolve ``chatbot`` vs ``predictive_model`` from explicit user input only.

    Accepted sources (first match wins):
    1. ``system_type`` argument
    2. ``monitoring_profile`` argument (alias)
    3. ``report["system_type"]`` or ``report["monitoring_profile"]`` when a report dict is passed
    """
    candidates = [
        system_type,
        monitoring_profile,
        (report or {}).get("system_type"),
        (report or {}).get("monitoring_profile"),
    ]

    resolved = next((c for c in candidates if c in VALID_SYSTEM_TYPES), None)

    if resolved is None:
        raise SystemTypeRequiredError(
            "system_type is required. Set system_type to 'chatbot' or 'predictive_model' "
            "(or monitoring_profile with the same values). Automatic detection is disabled."
        )

    return {
        "system_type": resolved,
        "classification_confidence": 1.0,
        "classification_source": "user_input",
    }


# Backward-compatible alias
def classify_monitoring_target(
    data: Any = None,
    *,
    system_type: str | None = None,
    monitoring_profile: str | None = None,
    hint_report: dict | None = None,
) -> dict[str, Any]:
    return resolve_system_type(
        system_type=system_type,
        monitoring_profile=monitoring_profile,
        report=hint_report,
    )
