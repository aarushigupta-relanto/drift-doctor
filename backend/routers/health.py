import time, os, sys
from fastapi import APIRouter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.agent_client import check_agent_health

router = APIRouter(prefix="/api", tags=["health"])
_START = time.time()

@router.get("/health")
async def health():
    agent = await check_agent_health()
    return {"status": "ok", "redis": "n/a", "agent": agent, "db": "ok", "uptime_s": int(time.time() - _START)}
