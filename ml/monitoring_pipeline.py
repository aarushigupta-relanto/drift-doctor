"""
Dual monitoring architecture entry point.

incoming traffic → system classifier → predictive OR chatbot monitor → enriched report
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ml.system_classifier import (
    resolve_system_type,
    SystemTypeRequiredError,
    classify_monitoring_target,
)
from ml.predictive_monitor import run_predictive_monitoring
from ml.chatbot_monitor import run_chatbot_monitoring
from ml.simulated_chatbot_data import get_current_conversations
from ml.production_data import load_production_sample
from ml.run_config import MLRunConfig


def run_monitoring(
    data: Any = None,
    *,
    system_type: str | None = None,
    monitoring_profile: str | None = None,
    reference_data: Any = None,
    use_simulated_chatbot: bool = False,
    config: MLRunConfig | None = None,
) -> dict[str, Any]:
    """
    Run the appropriate monitoring pipeline.

    Parameters
    ----------
    data :
        - pandas DataFrame with user_query/intent columns → predictive monitor
        - list[dict] with user_query + bot_response → chatbot monitor
    system_type :
        Required. ``predictive_model`` or ``chatbot`` (no auto-detection).
    monitoring_profile :
        Optional alias for ``system_type``.
    reference_data :
        Chatbot reference window (list of records). Defaults to simulated baseline.
    use_simulated_chatbot :
        If True and no data provided, run chatbot monitor on demo traffic.
    """
    cfg = config or MLRunConfig.default()

    if use_simulated_chatbot and data is None:
        data = get_current_conversations()

    classification = classify_monitoring_target(
        data,
        system_type=system_type,
        monitoring_profile=monitoring_profile,
    )
    resolved_type = classification["system_type"]

    if resolved_type == "chatbot":
        if data is None:
            data = get_current_conversations()
        report = run_chatbot_monitoring(data, reference_data)
    else:
        if data is None:
            data = load_production_sample(config=cfg)
        elif not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        report = run_predictive_monitoring(
            data,
            reference_path=cfg.dataset_path,
            model_path=cfg.reference_model_path,
        )

    report["classification"] = classification
    report["run_config"] = cfg.to_dict()
    return report


def run_drift_check(
    current_df: pd.DataFrame | None = None,
    *,
    system_type: str,
) -> dict[str, Any]:
    """Backward-compatible alias — requires explicit system_type."""
    if current_df is None:
        raise ValueError("run_drift_check requires current_df for predictive monitoring.")
    if not system_type:
        raise SystemTypeRequiredError(
            "run_drift_check requires system_type='predictive_model' or 'chatbot'."
        )
    return run_monitoring(current_df, system_type=system_type)


def run_chatbot_check(
    current: Any | None = None,
    reference: Any | None = None,
) -> dict[str, Any]:
    """Run chatbot monitoring (simulated data by default)."""
    return run_monitoring(
        current or get_current_conversations(),
        system_type="chatbot",
        reference_data=reference,
    )


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("CHATBOT MONITOR (simulated)")
    print("=" * 60)
    chatbot_report = run_chatbot_check()
    print(json.dumps(chatbot_report, indent=2))

    print("\n" + "=" * 60)
    print("PREDICTIVE MONITOR (requires final_dataset.csv + models)")
    print("=" * 60)
    try:
        import pandas as pd
        import os

        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "final_dataset.csv")
        df = pd.read_csv(data_path)
        prod = df[df["drift_tag"] == "clean_web"].head(100)
        if not prod.empty:
            pred_report = run_monitoring(prod, system_type="predictive_model")
            print(json.dumps({
                k: pred_report[k]
                for k in ("system_type", "drift_detected", "severity", "drift_types", "predictive_metrics")
            }, indent=2))
        else:
            print("No clean_web rows in dataset.")
    except Exception as exc:
        print(f"Skipped predictive demo: {exc}")
