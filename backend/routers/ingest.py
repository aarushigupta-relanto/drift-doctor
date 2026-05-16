import csv, os, logging, sys
from fastapi import APIRouter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.db.database import save_chat_log

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["ingest"])
CSV_PATH = "data/processed/current.csv"
CSV_HEADERS = ["timestamp","user_message","intent","response_time_ms","confidence","session_id"]

@router.post("")
async def ingest_log(log: dict):
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header: writer.writeheader()
        writer.writerow({k: log.get(k, "") for k in CSV_HEADERS})
    await save_chat_log(log)
    return {"received": True, "queued_for_detection": True}
