import asyncio
import logging
import os
import sys
import uuid

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.db.database import (
    get_latest_drift,
    get_retrain_history,
    get_retrain_task,
    save_retrain_task,
    update_retrain_task,
)
from backend.ws.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/retrain", tags=["retrain"])

_PROGRESS = {
    "queued": "Queued — waiting to start",
    "running": "Running retraining pipeline",
    "training": "Training candidate model on historical + production windows",
    "validating": "Validating candidate vs deployed reference model",
    "completed": "Retraining complete",
    "failed": "Retraining failed",
}


@router.post("/trigger", status_code=202)
async def trigger_retrain(req: dict):
    strategy = req.get("strategy")
    requested_by = req.get("requested_by", "user")
    drift_types = req.get("drift_types")

    task_id = str(uuid.uuid4())
    await save_retrain_task(task_id, strategy or "auto", requested_by)
    asyncio.create_task(_run_retrain(task_id, strategy, drift_types))
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Retrain task queued successfully",
    }


@router.get("/status/{task_id}")
async def retrain_status(task_id: str):
    task = await get_retrain_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    result = task.get("result") or {}
    phase = result.get("phase") if task["status"] == "running" else None
    progress = phase or _PROGRESS.get(task["status"], task["status"])

    return {
        "task_id": task_id,
        "status": task["status"],
        "strategy": task.get("strategy"),
        "progress": progress,
        "result": result if task["status"] in ("completed", "failed", "deployed") else None,
        "created_at": task.get("created_at"),
    }


@router.get("/history")
async def retrain_history(limit: int = 20):
    rows = await get_retrain_history(limit=limit)
    return {"runs": rows}


async def _run_retrain(
    task_id: str,
    strategy: str | None,
    drift_types: list[str] | None,
):
    from ml.retraining_pipeline import run_retraining_pipeline
    from ml.run_config import MLRunConfig

    cfg = MLRunConfig.default()

    async def broadcast(phase: str, partial: dict | None = None):
        payload = {"task_id": task_id, "status": "running", "phase": phase}
        if partial:
            payload["result"] = partial
        await manager.broadcast("retrain", payload)
        await update_retrain_task(
            task_id,
            "running",
            {"phase": phase, **(partial or {})},
        )

    try:
        await update_retrain_task(task_id, "running", {"phase": "queued"})
        await broadcast("loading_data")

        latest = await get_latest_drift()
        drift_report = (latest or {}).get("report")
        if not drift_types and drift_report:
            drift_types = drift_report.get("drift_types")

        loop = asyncio.get_event_loop()
        await broadcast("training")

        report = await loop.run_in_executor(
            None,
            lambda: run_retraining_pipeline(
                strategy=strategy,
                drift_types=drift_types,
                drift_report=drift_report,
                config=cfg,
            ),
        )
        await broadcast("validating")

        if report.get("status") == "failed" or report.get("error"):
            await update_retrain_task(
                task_id,
                "failed",
                {"error": report.get("error", "Unknown error"), **report},
            )
            await manager.broadcast(
                "retrain",
                {"task_id": task_id, "status": "failed", "result": report},
            )
            return

        final_status = "completed"
        await update_retrain_task(task_id, final_status, report)
        await manager.broadcast(
            "retrain",
            {"task_id": task_id, "status": final_status, "result": report},
        )
    except Exception as e:
        logger.exception("Retrain task %s failed", task_id)
        err = {"error": str(e), "status": "failed"}
        await update_retrain_task(task_id, "failed", err)
        await manager.broadcast(
            "retrain",
            {"task_id": task_id, "status": "failed", "result": err},
        )
