import logging
import os
import sys

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.agent_client import call_agent_explain
from backend.db.database import save_drift_event
from backend.ws.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.post("/run")
async def run_monitor(payload: dict):
    """
    Execute ML dual monitoring pipeline and optionally forward to the reasoning agent.

    Body examples:
      { "system_type": "chatbot", "use_simulated_chatbot": true }
      { "system_type": "predictive_model", "use_simulated_chatbot": false }
      { "records": [ { "user_query": "...", "bot_response": "...", ... } ] }
    """
    from ml.monitoring_pipeline import run_monitoring
    from ml.simulated_chatbot_data import get_current_conversations

    system_type = payload.get("system_type") or payload.get("monitoring_profile")
    if system_type not in ("chatbot", "predictive_model"):
        raise HTTPException(
            status_code=400,
            detail="system_type is required: 'chatbot' or 'predictive_model'",
        )

    use_simulated = payload.get("use_simulated_chatbot", False)
    records = payload.get("records")
    reference = payload.get("reference_records")
    explain = payload.get("explain", True)

    data = records
    if use_simulated and not records:
        data = get_current_conversations()

    from ml.run_config import MLRunConfig

    ml_config = (
        MLRunConfig.default()
        if system_type == "predictive_model"
        else None
    )

    try:
        report = run_monitoring(
            data,
            system_type=system_type,
            monitoring_profile=payload.get("monitoring_profile"),
            reference_data=reference,
            use_simulated_chatbot=use_simulated,
            config=ml_config,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    diagnosis = None
    if explain:
        diagnosis = await call_agent_explain(report)

    if not diagnosis:
        op = report.get("operational_assessment") or {}
        remediation = report.get("remediation") or {}
        diagnosis = {
            "production_risk": report.get("production_risk") or op.get("production_risk"),
            "retraining_necessity": report.get("retraining_necessity")
            or op.get("retraining_necessity"),
            "retrain_strategy": report.get("retrain_strategy")
            or op.get("recommended_strategy")
            or remediation.get("primary_action"),
            "operational_severity": op.get("operational_severity") or report.get("severity"),
            "drift_types": report.get("drift_types", []),
            "source": "ml_report_fallback",
        }

    if payload.get("persist", True):
        event_id = await save_drift_event(
            severity=report.get("severity", "LOW"),
            drift_share=report.get("drift_share", 0.0),
            report=report,
            diagnosis=diagnosis,
        )
        await manager.broadcast(
            "drift",
            {"event_id": event_id, "report": report, "diagnosis": diagnosis},
        )
        return {"event_id": event_id, "report": report, "diagnosis": diagnosis}

    return {"report": report, "diagnosis": diagnosis}
