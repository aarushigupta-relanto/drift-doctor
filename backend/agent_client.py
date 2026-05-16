import httpx, logging, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8001")
logger = logging.getLogger(__name__)
TIMEOUT = httpx.Timeout(30.0)

async def call_agent_explain(drift_payload: dict) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{AGENT_URL}/explain", json=drift_payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Agent /explain failed: {e}")
        return None

async def call_agent_chat(message: str, context: dict) -> str:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{AGENT_URL}/chat", json={"message": message, "context": context})
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception as e:
        logger.warning(f"Agent /chat failed: {e}")
        return "AI agent is currently offline. Please try again shortly."

async def check_agent_health() -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{AGENT_URL}/health")
            resp.raise_for_status()
            return "connected"
    except Exception:
        return "error"
