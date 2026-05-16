import logging, sys, os
from fastapi import APIRouter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.db.database import get_latest_drift
from backend.agent_client import call_agent_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("")
async def chat(req: dict):
    message = req.get("message", "")
    context = {}
    latest = await get_latest_drift()
    if latest:
        context = {"drift_share": latest.get("drift_share"), "severity": latest.get("severity"),
                   "timestamp": latest.get("timestamp"),
                   "diagnosis": latest.get("diagnosis", {}).get("diagnosis") if latest.get("diagnosis") else None}
    response_text = await call_agent_chat(message, context)
    return {"response": response_text, "context_used": context}
